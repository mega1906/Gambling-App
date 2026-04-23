from app.db import get_connection, get_server_connection
from app.settings import database_settings


def initialize_database():
    server_connection = get_server_connection()
    server_cursor = server_connection.cursor()

    try:
        server_cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {database_settings.database} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    finally:
        server_cursor.close()
        server_connection.close()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS gamblers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                phone_number VARCHAR(20),
                initial_stake DECIMAL(10, 2) NOT NULL,
                current_stake DECIMAL(10, 2) NOT NULL,
                win_threshold DECIMAL(10, 2) NOT NULL,
                loss_threshold DECIMAL(10, 2) NOT NULL,
                account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                total_bets INT NOT NULL DEFAULT 0,
                total_wins INT NOT NULL DEFAULT 0,
                total_losses INT NOT NULL DEFAULT 0,
                total_winnings DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CHECK (initial_stake > 0),
                CHECK (current_stake >= 0),
                CHECK (win_threshold > initial_stake),
                CHECK (loss_threshold >= 0),
                CHECK (loss_threshold < initial_stake)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS betting_preferences (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gambler_id INT NOT NULL,
                min_bet DECIMAL(10, 2) NOT NULL,
                max_bet DECIMAL(10, 2) NOT NULL,
                preferred_game_type VARCHAR(50) NOT NULL DEFAULT 'CUSTOM',
                session_game_limit INT NOT NULL DEFAULT 20,
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT fk_preferences_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE,
                CHECK (min_bet > 0),
                CHECK (max_bet >= min_bet),
                CHECK (session_game_limit > 0)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stake_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gambler_id INT NOT NULL,
                transaction_type VARCHAR(30) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                balance_before DECIMAL(10, 2) NOT NULL,
                balance_after DECIMAL(10, 2) NOT NULL,
                note VARCHAR(255),
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_stake_transactions_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE
            )
            """
        )
        cursor.execute("SHOW COLUMNS FROM betting_preferences LIKE 'auto_play'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE betting_preferences DROP COLUMN auto_play")
        connection.commit()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

    return {
        "database": database_settings.database,
        "tables": tables,
    }
