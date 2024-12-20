import arcade
from utils.constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, GROUND_HEIGHT, OBSTACLE_SPAWN_RATE, BUG_MAX_COUNT, BUG_MIN_COUNT, BUG_SCALE, BUG_SPEED
from entities.player import Player
from entities.obstacle import Obstacle
from entities.ground import Ground
import random
from entities.coin import Coin
import os
from entities.lightning_bug import LightningBug
import pyglet


class GameWindow(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.set_background_color(arcade.color.SKY_BLUE)
        self.player = None
        self.ground = None
        self.obstacles = None

        # Initialize the score
        self.score = 0
        self.running_speed = 200  # Player's initial running speed in pixels per second
        self.pixels_to_meters = 0.1  # Conversion factor: 10 pixels = 1 meter
        self.speed_increase_rate = 1  # Pixels per second increase every second
        self.max_running_speed = 5000  # Optional: Maximum running speed

        # Initialize scores
        self.scores = []
        self.load_scores()
        self.time_since_last_obstacle = 0
        self.time_since_last_coin = 0
        self.time_since_last_bug = 0
        self.game_over = False

        self.coins = arcade.SpriteList()
        self.lightning_bugs = arcade.SpriteList()
        self.total_coins_collected = 0

        # Background layers
        self.background_layers = []
        self.background_speeds = [0.2, 0.5, 1.0, 2.0]  # Parallax speeds
        self.background_offsets = [0, 0, 0, 0]  # Track each layer's horizontal offset

        # Background sound
        self.background_sound = None
        
        # Initialize the wind sound timer and interval
        self.wind_sound_timer = 0
        self.next_wind_interval = random.uniform(10, 25)  # 10 to 25 seconds
        self.wind_sound = None
        self.wind_sound_playing = False

        # Running sound
        self.running_sound = None
        self.running_sound_playing = False  # Track if the sound is already playing
        self.running_sound_player = None  # Playback instance for the running sound

        # Dialogue sound
        self.level_dialogue = None

    ################################################################################################
    # Initialization and Setup
    ################################################################################################
    def setup(self):
        """Setup the game and initialize objects."""       
        # Initialize game objects
        self.ground = Ground()
        self.player = Player()
        self.obstacles = arcade.SpriteList()
        
        # Load the total coins collected
        self.load_total_coins()

        # Load background layers
        for i in range(1, 5):  # Load Background1.png to Background4.png
            layer = arcade.load_texture(f"assets/images/background/Background{i}.png")
            self.background_layers.append(layer)
            
        # Play the background sound
        self.play_background_sound()
        self.play_wind_sound()
        
        # Schedule level dialogue to play with a delay
        arcade.schedule(self.delayed_play_level_dialogue, 1.0)  # 1-second delay

        # Load the running sound
        try:
            self.running_sound = arcade.Sound("assets/sounds/characters/running.wav")
        except Exception as e:
            print(f"Error loading running sound: {e}")
            
    def delayed_play_level_dialogue(self, delta_time):
        """Play the dialogue sound after a delay."""
        try:
            self.level_dialogue = arcade.Sound("assets/sounds/characters/dialogue/Level1_1.wav")
            self.level_dialogue.play(volume=2)
            # print("Level dialogue started.")
        except Exception as e:
            print(f"Error playing level dialogue: {e}")
        finally:
            # Cancel further scheduling of this method
            arcade.unschedule(self.delayed_play_level_dialogue)
            
    def play_background_sound(self):
        """Play and loop the background sound and periodically play wind sound."""
        try:
            # Play and loop the forest background sound
            self.background_sound = arcade.Sound("assets/sounds/background/forest_noises.wav")
            self.background_sound_player = self.background_sound.play(loop=True, volume=1)
        except Exception as e:
            print(f"Error playing background sound: {e}")

        # Ensure the wind sound is loaded
        try:
            self.wind_sound = arcade.Sound("assets/sounds/background/wind.wav")
            self.wind_sound_player = None  # To track if wind sound is playing
        except Exception as e:
            print(f"Error loading wind sound: {e}")
            self.wind_sound = None


    # Schedule wind sound playbackdef play_wind_sound(self):
    def play_wind_sound(self):
        """Periodically play the wind sound at random intervals."""
        try:
            # Ensure the wind sound is loaded
            self.wind_sound = arcade.Sound("assets/sounds/background/wind.wav")
        except Exception as e:
            print(f"Error loading wind sound: {e}")
            self.wind_sound = None

        def play_wind(delta_time):
            """Play the wind sound if it's not already playing."""
            if not self.wind_sound_playing and self.wind_sound is not None:
                try:
                    print("Wind sound starting...")
                    self.wind_sound.play()
                    self.wind_sound_playing = True
                    # Schedule flag reset after sound duration
                    sound_duration = self.wind_sound.get_length()
                    arcade.schedule(reset_wind_sound_flag, sound_duration)
                except Exception as e:
                    print(f"Error playing wind sound: {e}")

            # Schedule the next wind sound after a random interval
            next_interval = random.uniform(10, 25)
            arcade.schedule(play_wind, next_interval)

        def reset_wind_sound_flag(delta_time):
            """Reset the wind sound playing flag."""
            print("Wind sound stopping...")
            self.wind_sound_playing = False
            arcade.unschedule(reset_wind_sound_flag)

        # Initial scheduling
        arcade.schedule(play_wind, random.uniform(10, 25))

    ################################################################################################
    # Rendering
    ################################################################################################
    def on_draw(self):
        """Render all visual elements."""
        self.clear()

        # Draw background layers
        for i, layer in enumerate(self.background_layers):
            offset = self.background_offsets[i] % SCREEN_WIDTH
            arcade.draw_lrwh_rectangle_textured(-offset, 0, SCREEN_WIDTH, SCREEN_HEIGHT, layer)
            arcade.draw_lrwh_rectangle_textured(SCREEN_WIDTH - offset, 0, SCREEN_WIDTH, SCREEN_HEIGHT, layer)

        # Draw lightning bugs
        self.lightning_bugs.draw()

        # Render game objects
        self.ground.draw()
        self.player.draw()
        self.obstacles.draw()
        self.coins.draw()

        # Draw distance (score) in meters
        rounded_score = round(self.score)
        arcade.draw_text(f"Distance: {rounded_score} m", 10, SCREEN_HEIGHT - 30, arcade.color.WHITE, 20)

    ################################################################################################
    # Game Updates
    ################################################################################################
    def on_update(self, delta_time):
        """Update game state."""
        if self.game_over:
            # print("Game over reached. Saving coins...")
            
            # Stop the running sound if it's playing
            if self.running_sound_playing:
                # print("Stopping running sound due to game over.")
                if self.running_sound_player:
                    try:
                        self.running_sound.stop(self.running_sound_player)  # Ensure sound is fully stopped
                        # print("Running sound stopped due to game over.")
                    except Exception as e:
                        print(f"Error stopping running sound: {e}")
                else:
                    print("No running sound instance to stop.")
                
                self.running_sound_playing = False  # Update after stopping the sound

            # Save coins and return early
            self.save_total_coins()  # Save total coins collected
            return
        
        # Gradually increase the running speed
        self.running_speed += self.speed_increase_rate * delta_time
        if self.running_speed > self.max_running_speed:
            self.running_speed = self.max_running_speed  # Cap the running speed
        
        # Update the distance score
        self.score += self.running_speed * delta_time * self.pixels_to_meters

        # Update background offsets
        for i in range(len(self.background_layers)):
            self.background_offsets[i] += self.background_speeds[i]

        # Update ground tiles
        ground_scroll_speed = 200  # Pixels per second
        self.ground.update(delta_time, ground_scroll_speed)

        # Check if the player is on the ground by comparing their center_y to the ground height
        is_on_ground = self.player.center_y <= GROUND_HEIGHT + self.player.height / 2 + 1  # Allow for a small margin

        if not self.game_over and is_on_ground:
            # Start running sound if not already playing
            if not self.running_sound_playing and self.running_sound:
                # print("Player is on the ground. Starting running sound.")
                try:
                    self.running_sound_player = self.running_sound.play(loop=True, volume=1)
                    self.running_sound_playing = True
                    # print("Running sound started.")
                except Exception as e:
                    print(f"Error playing running sound: {e}")
        else:
            # Stop running sound if the player is in the air or the game is over
            if self.running_sound_playing:
                # print("Stopping running sound. Player is not on the ground or game is over.")
                if self.running_sound_player:
                    try:
                        self.running_sound.stop(self.running_sound_player)
                        self.running_sound_player = None  # Clear the player instance
                        # print("Running sound stopped.")
                    except Exception as e:
                        print(f"Error stopping running sound: {e}")
                self.running_sound_playing = False

        # Update player animation
        self.player.update_animation(delta_time)

        # Update game objects
        self.player.update()
        for obstacle in self.obstacles:
            obstacle.update(self.running_speed)
        for coin in self.coins:
            coin.update(delta_time, self.player, self.running_speed)
        self.lightning_bugs.update()

        # Update animations for obstacles and bugs
        for obstacle in self.obstacles:
            obstacle.update_animation(delta_time)
        for coin in self.coins:
            coin.update_animation(delta_time)
        for bug in self.lightning_bugs:
            bug.update_animation(delta_time)

        # Remove off-screen bugs
        self.remove_off_screen_bugs()

        # Spawn lightning bugs periodically
        self.time_since_last_bug += delta_time
        if self.time_since_last_bug > 1:  # Adjust spawn rate as needed
            self.time_since_last_bug = 0
            self.spawn_lightning_bug()

        # Remove off-screen obstacles and coins
        self.remove_off_screen_obstacles()
        self.remove_off_screen_coins()

        # Spawn obstacles and coins periodically
        self.spawn_periodic_objects(delta_time)

        # Check for collisions with obstacles or coins
        self.handle_collisions()

    ################################################################################################
    # Event Handlers
    ################################################################################################
    def on_key_press(self, key, modifiers):
        """Handle key presses."""
        if key == arcade.key.SPACE:
            self.player.jump()
        elif key == arcade.key.ESCAPE:
            # Stop the running sound when opening the pause menu
            if self.running_sound_playing and self.running_sound_player:
                try:
                    self.running_sound.stop(self.running_sound_player)
                    self.running_sound_player = None
                    self.running_sound_playing = False
                except Exception as e:
                    print(f"Error stopping running sound when pausing: {e}")

            from menus.pause import Pause
            pause_menu = Pause(self)
            self.window.show_view(pause_menu)
    ################################################################################################
    # Spawning World Assets
    ################################################################################################
    def spawn_obstacle(self):
        """Spawn a new animated obstacle."""
        obstacle = Obstacle(SCREEN_WIDTH, GROUND_HEIGHT + 20)
        self.obstacles.append(obstacle)

    def spawn_coin(self):
        """Spawn a coin at a random position."""
        x = SCREEN_WIDTH  # Spawn at the right edge of the screen
        y = GROUND_HEIGHT + random.randint(20, 100)  # Spawn near the ground with slight variation
        coin = Coin(x, y)
        self.coins.append(coin)
        
    def spawn_lightning_bug(self):
        """Spawn multiple lightning bugs at random positions in the background."""
        num_bugs = random.randint(BUG_MIN_COUNT, BUG_MAX_COUNT)
        for _ in range(num_bugs):
            x = SCREEN_WIDTH + random.randint(0, 200)
            y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - 50)
            bug = LightningBug(x, y, scale=BUG_SCALE)
            bug.change_x = BUG_SPEED
            self.lightning_bugs.append(bug)


    ################################################################################################
    # Collision Handling
    ################################################################################################
    def handle_collisions(self):
        """Check and handle collisions with obstacles and coins."""
        obstacles_hit = arcade.check_for_collision_with_list(self.player, self.obstacles)
        coins_collected = arcade.check_for_collision_with_list(self.player, self.coins)

        # Handle obstacle collisions
        if obstacles_hit:
            # print("Obstacle hit detected. Setting game over...")
            self.game_over = True
            
            # Stop the background sound if it's playing
            if self.background_sound_player:
                try:
                    self.background_sound.stop(self.background_sound_player)
                    self.background_sound_player = None  # Clear the player instance
                    print("Background sound stopped due to game over.")
                except Exception as e:
                    print(f"Error stopping background sound: {e}")

            # Stop the running sound if it's playing
            if self.running_sound_playing and self.running_sound_player:
                try:
                    self.running_sound.stop(self.running_sound_player)
                    # print("Running sound stopped due to game over.")
                except Exception as e:
                    print(f"Error stopping running sound during game over: {e}")
                self.running_sound_playing = False

            # Add the current score to the scores list and save it
            if self.score not in self.scores and round(self.score) not in self.scores:
                rounded_score = round(self.score)
                self.scores.append(rounded_score)

            self.scores.sort(reverse=True)  # Sort scores in descending order
            self.save_scores()

            # Save coins before transitioning to the GameOver view
            # print("Saving total coins before transitioning.")
            self.save_total_coins()

            # Transition to GameOver view
            # print("Transitioning to GameOver view.")
            from menus.game_over import GameOver
            game_over_view = GameOver(self.score)
            self.window.show_view(game_over_view)



        # Handle coin collisions
        for coin in coins_collected:
            self.coins.remove(coin)  # Remove the coin from the sprite list
            self.coin_collection = arcade.Sound('assets/sounds/game_sounds/coin_collection.wav')
            self.coin_collection.play(volume=0.75) # Play the coin collection sound
            self.total_coins_collected += 1  # Update the total coins collected
            # print(f"Coin collected! Total coins: {self.total_coins_collected}")

    def load_scores(self):
        """Load the scores from a file."""
        try:
            with open("game_watcher/scores.txt", "r") as file:
                self.scores = []
                for line in file:
                    stripped_line = line.strip()
                    if stripped_line:  # Skip empty lines
                        try:
                            score = round(float(stripped_line))  # Handle floats gracefully
                            self.scores.append(score)
                        except ValueError:
                            print(f"Skipping invalid score: {stripped_line}")
        except FileNotFoundError:
            self.scores = []  # Start with an empty list if the file doesn't exist
            print("No scores file found. Starting fresh.")
        except Exception as e:
            print(f"Error loading scores: {e}")

    def save_scores(self):
        """Save the scores to a file."""
        try:
            os.makedirs("game_watcher", exist_ok=True)  # Ensure the directory exists

            # Sanitize scores to ensure only rounded integers are written
            self.scores = [round(score) for score in self.scores]
            self.scores = sorted(set(self.scores), reverse=True)  # Sort and remove duplicates

            # Write scores to file
            with open("game_watcher/scores.txt", "w") as file:
                for score in self.scores:
                    file.write(f"{score}\n")
                
                # Remove the last score if there are more than 1 score
                if len(self.scores) > 1:
                    self.scores.pop()  # Remove the last score
                
            print("Scores saved successfully.")
        except Exception as e:
            print(f"Error saving scores: {e}")

    ################################################################################################
    # Utility Functions
    ################################################################################################
    def remove_off_screen_bugs(self):
        """Remove lightning bugs that are off-screen."""
        for bug in self.lightning_bugs:
            if bug.center_x < -bug.width:
                self.lightning_bugs.remove(bug)

    def remove_off_screen_obstacles(self):
        """Remove obstacles that are off-screen and update score."""
        for obstacle in self.obstacles:
            if obstacle.center_x < -obstacle.width:
                self.obstacles.remove(obstacle)
                
    def remove_off_screen_coins(self):
        """Remove coins that are off-screen."""
        for coin in self.coins:
            if coin.center_x < -coin.width:
                self.coins.remove(coin)

    def spawn_periodic_objects(self, delta_time):
        """Spawn obstacles and coins periodically based on running speed."""
        # Adjust spawn intervals based on running speed
        adjusted_obstacle_spawn_rate = OBSTACLE_SPAWN_RATE / (self.running_speed / 200)
        adjusted_coin_spawn_rate = 1.0 / (self.running_speed / 200)  # Adjust as needed

        # Spawn obstacles periodically
        self.time_since_last_obstacle += delta_time
        if self.time_since_last_obstacle > adjusted_obstacle_spawn_rate:
            self.time_since_last_obstacle = 0
            self.spawn_obstacle()

        # Spawn coins periodically
        self.time_since_last_coin += delta_time
        if self.time_since_last_coin > adjusted_coin_spawn_rate:
            self.time_since_last_coin = 0
            self.spawn_coin()

    def load_total_coins(self):
        """Load the total number of coins collected from a file."""
        try:
            with open("game_watcher/total_coins.txt", "r") as file:
                self.total_coins_collected = int(file.read().strip())
        except FileNotFoundError:
            self.total_coins_collected = 0  # Start at 0 if the file doesn't exist

    def save_total_coins(self):
        """Save the total number of coins collected to a file."""
        try:
            # Ensure the directory exists
            os.makedirs("game_watcher", exist_ok=True)

            # Save the total coins to a file
            with open("game_watcher/total_coins.txt", "w") as file:
                file.write(str(self.total_coins_collected))
        except Exception as e:
            print(f"Error saving total coins: {e}")
