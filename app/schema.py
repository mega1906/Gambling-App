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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS betting_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gambler_id INT NOT NULL,
                strategy_type VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                total_bets INT NOT NULL DEFAULT 0,
                total_wins INT NOT NULL DEFAULT 0,
                total_losses INT NOT NULL DEFAULT 0,
                total_profit DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                started_at DATETIME NOT NULL,
                ended_at DATETIME NULL,
                CONSTRAINT fk_betting_sessions_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gambler_id INT NOT NULL,
                session_id INT NULL,
                strategy_type VARCHAR(40) NOT NULL,
                bet_amount DECIMAL(10, 2) NOT NULL,
                win_probability DECIMAL(5, 4) NOT NULL,
                odds_multiplier DECIMAL(10, 2) NOT NULL,
                outcome VARCHAR(10) NOT NULL,
                payout_amount DECIMAL(10, 2) NOT NULL,
                stake_before DECIMAL(10, 2) NOT NULL,
                stake_after DECIMAL(10, 2) NOT NULL,
                placed_at DATETIME NOT NULL,
                settled_at DATETIME NOT NULL,
                CONSTRAINT fk_bets_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_bets_session
                    FOREIGN KEY (session_id) REFERENCES betting_sessions(id)
                    ON DELETE SET NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bet_id INT NOT NULL,
                gambler_id INT NOT NULL,
                outcome_strategy VARCHAR(30) NOT NULL,
                result_type VARCHAR(10) NOT NULL,
                payout_amount DECIMAL(10, 2) NOT NULL,
                net_change DECIMAL(10, 2) NOT NULL,
                stake_before DECIMAL(10, 2) NOT NULL,
                stake_after DECIMAL(10, 2) NOT NULL,
                win_probability DECIMAL(5, 4) NOT NULL,
                house_edge DECIMAL(5, 4) NOT NULL DEFAULT 0.0000,
                current_win_streak INT NOT NULL DEFAULT 0,
                current_loss_streak INT NOT NULL DEFAULT 0,
                longest_win_streak INT NOT NULL DEFAULT 0,
                longest_loss_streak INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                CONSTRAINT fk_game_results_bet
                    FOREIGN KEY (bet_id) REFERENCES bets(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_game_results_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS gaming_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                gambler_id INT NOT NULL,
                status VARCHAR(20) NOT NULL,
                end_reason VARCHAR(40) NULL,
                default_bet_amount DECIMAL(10, 2) NOT NULL,
                default_win_probability DECIMAL(5, 4) NOT NULL,
                max_games INT NOT NULL,
                total_games_played INT NOT NULL DEFAULT 0,
                total_wins INT NOT NULL DEFAULT 0,
                total_losses INT NOT NULL DEFAULT 0,
                total_profit DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                total_pause_seconds INT NOT NULL DEFAULT 0,
                started_at DATETIME NOT NULL,
                ended_at DATETIME NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT fk_gaming_sessions_gambler
                    FOREIGN KEY (gambler_id) REFERENCES gamblers(id)
                    ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS game_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                bet_id INT NOT NULL,
                game_number INT NOT NULL,
                bet_amount DECIMAL(10, 2) NOT NULL,
                outcome VARCHAR(10) NOT NULL,
                payout_amount DECIMAL(10, 2) NOT NULL,
                stake_before DECIMAL(10, 2) NOT NULL,
                stake_after DECIMAL(10, 2) NOT NULL,
                played_at DATETIME NOT NULL,
                CONSTRAINT fk_game_records_session
                    FOREIGN KEY (session_id) REFERENCES gaming_sessions(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_game_records_bet
                    FOREIGN KEY (bet_id) REFERENCES bets(id)
                    ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pause_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                pause_reason VARCHAR(100) NOT NULL,
                paused_at DATETIME NOT NULL,
                resumed_at DATETIME NULL,
                pause_seconds INT NOT NULL DEFAULT 0,
                CONSTRAINT fk_pause_records_session
                    FOREIGN KEY (session_id) REFERENCES gaming_sessions(id)
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
