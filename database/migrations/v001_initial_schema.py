"""
初始数据库结构迁移
创建游戏核心表结构
"""

from .base_migration import BaseMigration


class V001InitialSchema(BaseMigration):
    """初始数据库结构"""

    version = "001"
    description = "创建初始数据库表结构"

    async def up(self):
        """创建初始表结构"""
        # 玩家表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                realm_id TEXT DEFAULT 'realm_001',
                experience INTEGER DEFAULT 0,
                spirit_stone INTEGER DEFAULT 100,
                health INTEGER DEFAULT 100,
                max_health INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                defense INTEGER DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 物品表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                item_type TEXT NOT NULL,
                rarity TEXT DEFAULT 'common',
                effect_type TEXT,
                effect_value INTEGER DEFAULT 0,
                price INTEGER DEFAULT 0,
                is_usable INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 玩家背包表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_inventory (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                item_id TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                equipped INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (item_id) REFERENCES items(id),
                UNIQUE(player_id, item_id)
            )
        """)

        # 功法表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                skill_type TEXT NOT NULL,
                realm_requirement TEXT,
                experience_gain INTEGER DEFAULT 10,
                damage INTEGER DEFAULT 0,
                cooldown INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 玩家功法表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_skills (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                experience INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (skill_id) REFERENCES skills(id),
                UNIQUE(player_id, skill_id)
            )
        """)

        # 境界表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS realms (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                level INTEGER NOT NULL,
                experience_required INTEGER NOT NULL,
                health_bonus INTEGER DEFAULT 0,
                attack_bonus INTEGER DEFAULT 0,
                defense_bonus INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 游戏事件表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS game_events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                event_type TEXT NOT NULL,
                trigger_condition TEXT,
                reward_type TEXT,
                reward_value INTEGER DEFAULT 0,
                probability REAL DEFAULT 0.5,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 玩家事件记录表
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS player_events (
                id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (event_id) REFERENCES game_events(id)
            )
        """)

        await self.db.commit()

    async def down(self):
        """回滚初始表结构"""
        tables = [
            "player_events",
            "game_events",
            "player_skills",
            "skills",
            "player_inventory",
            "items",
            "players",
            "realms",
        ]
        for table in tables:
            await self.db.execute(f"DROP TABLE IF EXISTS {table}")
        await self.db.commit()
