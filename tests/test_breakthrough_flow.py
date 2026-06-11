"""
突破流程端到端测试

覆盖三种突破场景:
1. 凡人→炼气（无条件自动突破）
2. 炼气圆满→筑基初期（auto条件+物品需求）
3. 筑基圆满→金丹初期（manual条件+物品需求）

测试重点:
- add_experience 统一入口的截断和溢出逻辑
- check_breakthrough_prompt 的差异化提示
- try_auto_breakthrough 的自动/手动突破分流
- PlayerStateChecker 的 condition_type 传递
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

# 在导入项目模块前 mock 掉 astrbot 及其依赖（避免依赖 loguru/alembic 等运行时库）
_mock_astrbot = MagicMock()
_mock_astrbot.api = MagicMock()
_mock_astrbot.api.logger = MagicMock()
_mock_astrbot.core = MagicMock()
_mock_astrbot.core.message = MagicMock()
_mock_astrbot.core.message.components = MagicMock()
_mock_astrbot.core.message.components.Plain = MagicMock
sys.modules.setdefault("astrbot", _mock_astrbot)
sys.modules.setdefault("astrbot.api", _mock_astrbot.api)
sys.modules.setdefault("astrbot.core", _mock_astrbot.core)
sys.modules.setdefault("astrbot.core.message", _mock_astrbot.core.message)
sys.modules.setdefault("astrbot.core.message.components", _mock_astrbot.core.message.components)

# 将 AstrBot 插件父目录加入 sys.path，使插件可作为包导入
PLUGIN_ROOT = Path(__file__).parent.parent
ASTRBOT_PLUGINS_DIR = PLUGIN_ROOT.parent
sys.path.insert(0, str(ASTRBOT_PLUGINS_DIR))

# mock alembic（测试环境不需要数据库迁移）
sys.modules.setdefault("alembic", MagicMock())
sys.modules.setdefault("alembic.command", MagicMock())
sys.modules.setdefault("alembic.config", MagicMock())
sys.modules.setdefault("alembic.migration", MagicMock())
sys.modules.setdefault("alembic.operations", MagicMock())
sys.modules.setdefault("alembic.operations.ops", MagicMock())
sys.modules.setdefault("alembic.runtime", MagicMock())
sys.modules.setdefault("alembic.runtime.migration", MagicMock())
sys.modules.setdefault("alembic.script", MagicMock())
sys.modules.setdefault("alembic.script.revision", MagicMock())

# mock astrbot_plugin_xiuxian_shell.services 中测试不需要的模块（避免级联导入失败）
PLUGIN_PKG = "astrbot_plugin_xiuxian_shell"
for svc in [
    "notification_service", "market_service", "admin_server",
    "item_effect_service", "deep_seclusion_service",
]:
    sys.modules.setdefault(f"{PLUGIN_PKG}.services.{svc}", MagicMock())


# ==================== Fixtures ====================

@pytest_asyncio.fixture
async def db(tmp_path):
    """创建测试数据库并初始化表结构"""
    from astrbot_plugin_xiuxian_shell.database.db_manager import DatabaseManager

    db_path = str(tmp_path / "test.db")
    db_manager = DatabaseManager(db_path)
    await db_manager.connect()

    # 创建 players 表
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL DEFAULT 'test',
            realm_id TEXT DEFAULT 'realm_001',
            experience INTEGER DEFAULT 0,
            temp_experience INTEGER DEFAULT 0,
            spirit_stone INTEGER DEFAULT 100,
            health INTEGER DEFAULT 100,
            max_health INTEGER DEFAULT 100,
            mp INTEGER DEFAULT 50,
            stamina INTEGER DEFAULT 100,
            bone INTEGER DEFAULT 5,
            spirit INTEGER DEFAULT 5,
            intel INTEGER DEFAULT 5,
            str INTEGER DEFAULT 5,
            percep INTEGER DEFAULT 5,
            luck INTEGER DEFAULT 5,
            last_breakthrough_prompt TEXT,
            last_passive_exp TEXT,
            is_deleted INTEGER DEFAULT 0,
            ban_reason TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db_manager.commit()

    # 创建 realm_breakthrough_conditions 表
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS realm_breakthrough_conditions (
            id TEXT PRIMARY KEY,
            realm_id TEXT NOT NULL,
            realm_name TEXT NOT NULL,
            condition_type TEXT NOT NULL,
            item_requirements TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db_manager.commit()

    # 创建 items 表
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            item_type TEXT NOT NULL,
            effect_type TEXT,
            effect_value INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0,
            is_usable INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db_manager.commit()

    # 创建 player_inventory 表
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS player_inventory (
            id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            equipped INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_id, item_id)
        )
    """)
    await db_manager.commit()

    # 插入突破条件数据
    await db_manager.execute(
        "INSERT INTO realm_breakthrough_conditions (id, realm_id, realm_name, condition_type, item_requirements, description) VALUES (?, ?, ?, ?, ?, ?)",
        ("btc_001", "realm_006", "筑基初期", "auto", '[{"item_id":"item_zhuji_dan","item_name":"筑基丹","quantity":1}]', "突破筑基期需要服用筑基丹"),
    )
    await db_manager.execute(
        "INSERT INTO realm_breakthrough_conditions (id, realm_id, realm_name, condition_type, item_requirements, description) VALUES (?, ?, ?, ?, ?, ?)",
        ("btc_002", "realm_010", "金丹初期", "manual", '[{"item_id":"item_tianhuo_ye","item_name":"天火液","quantity":1}]', "结丹之劫"),
    )
    await db_manager.commit()

    # 插入突破物品
    await db_manager.execute(
        "INSERT INTO items (id, name, description, item_type, effect_type, effect_value, price, is_usable) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("item_zhuji_dan", "筑基丹", "筑基期突破必备", "material", "breakthrough", 0, 500, 0),
    )
    await db_manager.execute(
        "INSERT INTO items (id, name, description, item_type, effect_type, effect_value, price, is_usable) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("item_tianhuo_ye", "天火液", "结丹之劫必备", "material", "breakthrough", 0, 2000, 0),
    )
    await db_manager.commit()

    yield db_manager

    await db_manager.close()


@pytest_asyncio.fixture
async def cultivation_svc(db):
    """创建修炼服务实例"""
    from astrbot_plugin_xiuxian_shell.services.cultivation_service import CultivationService
    from astrbot_plugin_xiuxian_shell.services.cultivation_service import DEFAULT_REALMS_DATA
    from astrbot_plugin_xiuxian_shell.models.realm import Realm
    svc = CultivationService(db)
    # 直接用 DEFAULT_REALMS_DATA 初始化缓存（测试环境无 json_data_manager）
    svc._realms_cache = {realm["id"]: Realm.from_dict(realm) for realm in DEFAULT_REALMS_DATA}
    svc._realms_loaded = True
    return svc


@pytest_asyncio.fixture
async def breakthrough_svc(db, cultivation_svc):
    """创建突破服务实例"""
    from astrbot_plugin_xiuxian_shell.services.breakthrough_service import BreakthroughService
    return BreakthroughService(db, None, cultivation_svc)


@pytest_asyncio.fixture
async def full_setup(db, cultivation_svc, breakthrough_svc):
    """完整服务设置（含双向引用）"""
    cultivation_svc._breakthrough_service_ref = breakthrough_svc
    return db, cultivation_svc, breakthrough_svc


async def _create_player(db, player_id=None, realm_id="realm_001", experience=0):
    """辅助方法：创建测试玩家"""
    if not player_id:
        player_id = str(uuid.uuid4())
    user_id = f"user_{player_id[:8]}"
    await db.execute(
        """INSERT INTO players (id, user_id, username, realm_id, experience, temp_experience)
        VALUES (?, ?, ?, ?, ?, 0)""",
        (player_id, user_id, f"test_{player_id[:4]}", realm_id, experience),
    )
    await db.commit()
    return player_id


# ==================== 测试: add_experience 统一入口 ====================

@pytest.mark.asyncio
async def test_add_experience_basic(full_setup):
    """测试基础修为增加"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=0)

    result = await cultivation_svc.add_experience(player_id, 50)

    assert result["actual_change"] == 50
    assert result["current_exp"] == 50
    assert result["overflow"] == 0
    assert result["exp_cap"] == 100


@pytest.mark.asyncio
async def test_add_experience_truncation_and_overflow(full_setup):
    """测试修为截断和溢出：凡人修为上限100，90+110应截断到100"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=90)

    result = await cultivation_svc.add_experience(player_id, 110)

    assert result["current_exp"] == 100
    assert result["overflow"] == 100
    assert result["exp_cap"] == 100


@pytest.mark.asyncio
async def test_add_experience_exact_cap(full_setup):
    """测试修为刚好达到上限：90 + 10 = 100"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=90)

    result = await cultivation_svc.add_experience(player_id, 10)

    assert result["current_exp"] == 100
    assert result["overflow"] == 0


@pytest.mark.asyncio
async def test_add_experience_negative(full_setup):
    """测试修为减少不会降到0以下"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=30)

    result = await cultivation_svc.add_experience(player_id, -50)

    assert result["current_exp"] == 0


# ==================== 测试: check_breakthrough_prompt ====================

@pytest.mark.asyncio
async def test_breakthrough_prompt_no_condition(full_setup):
    """测试无条件境界的突破提示（凡人→炼气）"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=100)

    result = await cultivation_svc.check_breakthrough_prompt(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "none"
    assert "突破提示" in result["prompt_message"]
    assert "突破" in result["prompt_message"]
    assert "<突破>" in result["prompt_message"]


@pytest.mark.asyncio
async def test_breakthrough_prompt_auto_condition(full_setup):
    """测试auto条件境界的突破提示（炼气圆满→筑基初期）"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, realm_id="realm_005", experience=4000)

    result = await cultivation_svc.check_breakthrough_prompt(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "auto"
    assert "筑基丹" in result["prompt_message"]


@pytest.mark.asyncio
async def test_breakthrough_prompt_manual_condition(full_setup):
    """测试manual条件境界的突破提示（筑基圆满→金丹初期）"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    result = await cultivation_svc.check_breakthrough_prompt(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "manual"
    assert "手动发起突破" in result["prompt_message"]
    assert "天火液" in result["prompt_message"]


@pytest.mark.asyncio
async def test_breakthrough_prompt_daily_once(full_setup):
    """测试突破提示每天只提示一次"""
    db, cultivation_svc, _ = full_setup
    player_id = await _create_player(db, experience=100)

    result1 = await cultivation_svc.check_breakthrough_prompt(player_id)
    assert result1["prompt_message"] != ""

    result2 = await cultivation_svc.check_breakthrough_prompt(player_id)
    assert result2["prompt_message"] == ""
    assert result2["needs_breakthrough"] is True
    assert result2["condition_type"] == "none"


# ==================== 测试: try_auto_breakthrough ====================

@pytest.mark.asyncio
async def test_auto_breakthrough_no_condition(full_setup):
    """测试无条件自动突破（凡人→炼气初期）"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, experience=100)

    result = await breakthrough_svc.try_auto_breakthrough(player_id)

    assert result is not None
    assert result["success"] is True
    assert "炼气初期" in result["message"]

    player = await db.fetch_one("SELECT realm_id, experience FROM players WHERE id = ?", (player_id,))
    assert player["realm_id"] == "realm_002"
    assert player["experience"] == 0


@pytest.mark.asyncio
async def test_auto_breakthrough_auto_condition_with_items(full_setup):
    """测试auto条件+物品需求的自动突破（炼气圆满→筑基初期，有筑基丹）"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_005", experience=4000)

    inv_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
        (inv_id, player_id, "item_zhuji_dan", 1),
    )
    await db.commit()

    result = await breakthrough_svc.try_auto_breakthrough(player_id)

    assert result is not None
    assert result["success"] is True
    assert "筑基初期" in result["message"]


@pytest.mark.asyncio
async def test_auto_breakthrough_auto_condition_missing_items(full_setup):
    """测试auto条件+物品不足时静默返回"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_005", experience=4000)

    result = await breakthrough_svc.try_auto_breakthrough(player_id)

    assert result is not None
    assert result["success"] is False
    assert result.get("message") is None


@pytest.mark.asyncio
async def test_auto_breakthrough_manual_condition(full_setup):
    """测试manual条件不自动突破"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    result = await breakthrough_svc.try_auto_breakthrough(player_id)

    assert result is not None
    assert result["success"] is False
    assert result.get("is_manual_condition") is True
    assert result.get("message") is None


# ==================== 测试: PlayerStateChecker condition_type 传递 ====================

@pytest.mark.asyncio
async def test_state_checker_manual_skips_auto_breakthrough(full_setup):
    """测试 PlayerStateChecker 对 manual 条件不设置 needs_auto_breakthrough"""
    db, cultivation_svc, breakthrough_svc = full_setup
    from astrbot_plugin_xiuxian_shell.services.player_state_checker import PlayerStateChecker

    checker = PlayerStateChecker(db, cultivation_svc, breakthrough_svc)
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    result = await checker.check_player_state(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "manual"
    assert result["needs_auto_breakthrough"] is False  # manual 条件不自动突破


@pytest.mark.asyncio
async def test_state_checker_no_condition_triggers_auto(full_setup):
    """测试 PlayerStateChecker 对无条件境界设置 needs_auto_breakthrough"""
    db, cultivation_svc, breakthrough_svc = full_setup
    from astrbot_plugin_xiuxian_shell.services.player_state_checker import PlayerStateChecker

    checker = PlayerStateChecker(db, cultivation_svc, breakthrough_svc)
    player_id = await _create_player(db, experience=100)

    result = await checker.check_player_state(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "none"
    assert result["needs_auto_breakthrough"] is True


@pytest.mark.asyncio
async def test_state_checker_auto_condition_triggers_auto(full_setup):
    """测试 PlayerStateChecker 对 auto 条件境界设置 needs_auto_breakthrough"""
    db, cultivation_svc, breakthrough_svc = full_setup
    from astrbot_plugin_xiuxian_shell.services.player_state_checker import PlayerStateChecker

    checker = PlayerStateChecker(db, cultivation_svc, breakthrough_svc)
    player_id = await _create_player(db, realm_id="realm_005", experience=4000)

    result = await checker.check_player_state(player_id)

    assert result["needs_breakthrough"] is True
    assert result["condition_type"] == "auto"
    assert result["needs_auto_breakthrough"] is True


# ==================== 测试: try_manual_breakthrough ====================

@pytest.mark.asyncio
async def test_manual_breakthrough_success(full_setup):
    """测试手动突破成功（筑基圆满→金丹初期，有天火液）"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    inv_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO player_inventory (id, player_id, item_id, quantity) VALUES (?, ?, ?, ?)",
        (inv_id, player_id, "item_tianhuo_ye", 1),
    )
    await db.commit()

    with patch("random.random", return_value=0.0):
        result = await breakthrough_svc.try_manual_breakthrough(player_id)

    assert result["success"] is True
    assert "金丹初期" in result["message"]


@pytest.mark.asyncio
async def test_manual_breakthrough_missing_items(full_setup):
    """测试手动突破物品不足时的提示"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    result = await breakthrough_svc.try_manual_breakthrough(player_id)

    assert result["success"] is False
    assert "天火液" in result["message"]


@pytest.mark.asyncio
async def test_manual_breakthrough_exp_not_enough(full_setup):
    """测试手动突破修为不足"""
    db, cultivation_svc, breakthrough_svc = full_setup
    player_id = await _create_player(db, realm_id="realm_009", experience=5000)

    result = await breakthrough_svc.try_manual_breakthrough(player_id)

    assert result["success"] is False
    assert "修为不足" in result["message"]


# ==================== 测试: tick_all_players condition_type 传播 ====================

@pytest.mark.asyncio
async def test_tick_all_players_manual_no_auto_breakthrough(full_setup):
    """测试 tick_all_players 对 manual 条件不设置 needs_auto_breakthrough"""
    db, cultivation_svc, breakthrough_svc = full_setup
    from astrbot_plugin_xiuxian_shell.services.player_state_checker import PlayerStateChecker

    checker = PlayerStateChecker(db, cultivation_svc, breakthrough_svc)
    player_id = await _create_player(db, realm_id="realm_009", experience=12000)

    notifications = await checker.tick_all_players()

    target = [n for n in notifications if n["player_id"] == player_id]
    assert len(target) == 1
    assert target[0]["condition_type"] == "manual"
    assert target[0]["needs_auto_breakthrough"] is False


@pytest.mark.asyncio
async def test_tick_all_players_no_condition_triggers_auto(full_setup):
    """测试 tick_all_players 对无条件境界设置 needs_auto_breakthrough"""
    db, cultivation_svc, breakthrough_svc = full_setup
    from astrbot_plugin_xiuxian_shell.services.player_state_checker import PlayerStateChecker

    checker = PlayerStateChecker(db, cultivation_svc, breakthrough_svc)
    player_id = await _create_player(db, experience=100)

    notifications = await checker.tick_all_players()

    target = [n for n in notifications if n["player_id"] == player_id]
    assert len(target) == 1
    assert target[0]["condition_type"] == "none"
    assert target[0]["needs_auto_breakthrough"] is True
