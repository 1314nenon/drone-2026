import pygame
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK
from field import Field

class Player:
    def __init__(self):
        self.width = 20
        self.height = 20
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.rect = pygame.Rect(self.x - self.width // 2, self.y - self.height // 2, 
                                self.width, self.height)
        
        # Velocity
        self.vx = 0
        self.vy = 0
        
        # Physics parameters
        self.max_speed = 5.0  # Maximum velocity
        self.damping = 0.85  # Velocity damping (0-1, lower = more damping)
        
        # Field force parameters
        self.attractive_strength = 50
        self.repulsive_strength = 10000
        self.repulsive_influence_distance = 100
        
        # Virtual force (attraction weakening approach)
        self.base_attractive_strength = 200  # Store original strength
        self.weakening_active = False
        self.weakening_timer = 0.0
        self.weakening_duration = 10.0  # How long to weaken attraction
        self.velocity_boost_strength = 0.5  # From Java: vx = vx + 5
        
        # Local minima detection
        self.position_history = []
        self.stuck_threshold = 3.0  # seconds before considering stuck
        self.stuck_distance = 20.0  # If moved less than this distance, might be stuck
        self.stuck_timer = 0.0
        self.total_time = 0.0
        self.is_stuck = False

    def detect_local_minima(self, goal, dt):
        """Detect if player is stuck in a local minimum"""
        self.total_time += dt
        current_pos = (self.x, self.y)
        
        # Add current position to history with timestamp
        self.position_history.append((current_pos, self.total_time))
        
        # Keep only recent history
        self.position_history = [(pos, t) for pos, t in self.position_history 
                                  if self.total_time - t <= self.stuck_threshold]
        
        # Check if we're far from goal
        distance_to_goal = math.hypot(self.x - goal[0], self.y - goal[1])
        
        # If we're at the goal, we're not stuck
        if distance_to_goal < 15:
            self.stuck_timer = 0.0
            self.is_stuck = False
            self.weakening_active = False
            return False
        
        # Check if we've been moving very little
        if len(self.position_history) > 1:
            oldest_pos, _ = self.position_history[0]
            distance_moved = math.hypot(current_pos[0] - oldest_pos[0], 
                                       current_pos[1] - oldest_pos[1])
            
            speed = math.hypot(self.vx, self.vy)
            
            # RELAXED CONDITION - detect equilibrium state
            if distance_moved < self.stuck_distance and speed < 2.0:  # Increased threshold
                self.stuck_timer += dt
                
                # If stuck for long enough, activate weakening
                if self.stuck_timer >= self.stuck_threshold:
                    self.is_stuck = True
                    if not self.weakening_active:
                        self.weakening_active = True
                        self.weakening_timer = 0.0
                        print(f"!!! [Virtual Force] ACTIVATED for {self.weakening_duration}s")
                    return True
            else:
                # Don't reset as aggressively
                self.stuck_timer = max(0, self.stuck_timer - dt * 0.5)
                self.is_stuck = False
        
        return False

    def calculate_field_force(self, goal, obstacles):
        """Calculate the total force from attractive and repulsive fields"""
        if goal is None:
            return (0, 0)
        
        position = (self.x, self.y)
        total_fx, total_fy = 0, 0
        
        # Calculate current weakening factor and repulsion boost based on minS
        weakening_factor = 1.0
        repulsion_boost = 1.0
        influence_boost = 1.0
        
        if self.weakening_active:
            # First, calculate the intended direction from all forces
            temp_fx, temp_fy = 0, 0
            
            # Attractive force from goal (without weakening for direction calculation)
            fx, fy = Field.calculate_attractive_force(
                position, 
                goal, 
                strength=self.attractive_strength
            )
            temp_fx += fx
            temp_fy += fy
            
            # Repulsive forces
            for obstacle in obstacles:
                if hasattr(obstacle, 'is_trap') and obstacle.is_trap:
                    fx, fy = Field.calculate_repulsive_force_rect(
                        position,
                        obstacle.rect,
                        strength=self.repulsive_strength,
                        influence_distance=self.repulsive_influence_distance
                    )
                else:
                    fx, fy = Field.calculate_repulsive_force(
                        position,
                        obstacle.rect.center,
                        obstacle.width / 2,
                        strength=self.repulsive_strength,
                        influence_distance=self.repulsive_influence_distance
                    )
                temp_fx += fx
                temp_fy += fy
            
            # Normalize to get direction
            direction_magnitude = math.hypot(temp_fx, temp_fy)
            if direction_magnitude > 0:
                dirX = temp_fx / direction_magnitude
                dirY = temp_fy / direction_magnitude
                
                # Calculate minS (minimum safety)
                minS = Field.calculate_min_safety(position, (dirX, dirY), obstacles)
                
                print(f"minS = {minS:.1f}")
                
                # Adjust forces based on minS (YOUR TWEAKED VALUES)
                if minS < 5:
                    # Very blocked - weaken attraction, BOOST repulsion
                    weakening_factor = minS / 50
                    repulsion_boost = 1.0  # Triple repulsion strength
                    influence_boost = 1.0  # 50% wider influence
                    print(f"Path VERY blocked! Attraction: {weakening_factor:.2f}x, Repulsion: {repulsion_boost:.1f}x, Range: {influence_boost:.1f}x")
                elif minS < 50:
                    # Somewhat blocked - moderate adjustments
                    weakening_factor = 0.001
                    repulsion_boost = 1.0  # Double repulsion strength
                    influence_boost = 1.0  # 30% wider influence
                    print(f"Path blocked! Attraction: {weakening_factor:.2f}x, Repulsion: {repulsion_boost:.1f}x, Range: {influence_boost:.1f}x")
                else:
                    # Clear path - normal forces
                    weakening_factor = 0.05
                    repulsion_boost = 1.0
                    influence_boost = 1.0
                    print(f"Path clear! Normal forces")
            
            # Debug header
            print(f"=== FORCE COMPARISON ===")
            print(f"Weakening: {weakening_factor:.2f}x, Repulsion boost: {repulsion_boost:.1f}x")
        
        # Calculate attractive force
        fx, fy = Field.calculate_attractive_force(
            position, 
            goal, 
            strength=self.attractive_strength,
            weakening_factor=weakening_factor
        )
        total_fx += fx
        total_fy += fy
        
        # DEBUG: Print attractive force
        if self.weakening_active:
            print(f"Attractive force: ({fx:.1f}, {fy:.1f}), magnitude: {math.hypot(fx, fy):.1f}")
        
        # Repulsive forces from all obstacles (WITH boost and extended range)
        boosted_repulsion = self.repulsive_strength * repulsion_boost
        boosted_influence = self.repulsive_influence_distance * influence_boost
        
        repulsive_total_x = 0
        repulsive_total_y = 0
        
        for obstacle in obstacles:
            if hasattr(obstacle, 'is_trap') and obstacle.is_trap:
                fx, fy = Field.calculate_repulsive_force_rect(
                    position,
                    obstacle.rect,
                    strength=boosted_repulsion,
                    influence_distance=boosted_influence
                )
            else:
                fx, fy = Field.calculate_repulsive_force(
                    position,
                    obstacle.rect.center,
                    obstacle.width / 2,
                    strength=boosted_repulsion,
                    influence_distance=boosted_influence
                )
            total_fx += fx
            total_fy += fy
            repulsive_total_x += fx
            repulsive_total_y += fy
        
        # DEBUG: Print repulsive force
        if self.weakening_active:
            print(f"Repulsive force: ({repulsive_total_x:.1f}, {repulsive_total_y:.1f}), magnitude: {math.hypot(repulsive_total_x, repulsive_total_y):.1f}")
            print(f"Net force: ({total_fx:.1f}, {total_fy:.1f}), magnitude: {math.hypot(total_fx, total_fy):.1f}")
            print(f"=====================")
        
        return (total_fx, total_fy)
    
    def update_with_field(self, goal, obstacles, dt=1/60.0):
        """Update player position based on field forces"""
        if goal is None:
            return
        
        # Detect if stuck in local minimum
        self.detect_local_minima(goal, dt)
        
        # Calculate force from field (includes weakening and boosting if active)
        fx, fy = self.calculate_field_force(goal, obstacles)
        
        # Update velocity with force (treating force as acceleration)
        self.vx += fx * 0.01  # Scale factor to control responsiveness
        self.vy += fy * 0.01
        
        # VIRTUAL FORCE: Add velocity boost perpendicular to nearest obstacle
        if self.weakening_active:
            self.weakening_timer += dt
            
            # Find nearest obstacle
            min_dist = float('inf')
            nearest_obs = None
            for obstacle in obstacles:
                if hasattr(obstacle, 'is_trap') and obstacle.is_trap:
                    # Distance to rectangular obstacle
                    closest_x = max(obstacle.rect.left, min(self.x, obstacle.rect.right))
                    closest_y = max(obstacle.rect.top, min(self.y, obstacle.rect.bottom))
                    dist = math.hypot(self.x - closest_x, self.y - closest_y)
                else:
                    # Distance to circular obstacle
                    dist = math.hypot(self.x - obstacle.rect.centerx, self.y - obstacle.rect.centery)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_obs = obstacle
            
            if nearest_obs:
                # Calculate direction TO the nearest obstacle
                if hasattr(nearest_obs, 'is_trap') and nearest_obs.is_trap:
                    # For rectangular obstacle, use center
                    obs_x = nearest_obs.rect.centerx
                    obs_y = nearest_obs.rect.centery
                else:
                    obs_x = nearest_obs.rect.centerx
                    obs_y = nearest_obs.rect.centery
                
                # Direction vector from player to obstacle
                to_obs_x = obs_x - self.x
                to_obs_y = obs_y - self.y
                
                # Normalize
                mag = math.hypot(to_obs_x, to_obs_y)
                if mag > 0:
                    to_obs_x /= mag
                    to_obs_y /= mag
                    
                    # Get perpendicular direction (rotate 90 degrees to the right)
                    # If direction is (x, y), right perpendicular is (y, -x)
                    perp_x = to_obs_y
                    perp_y = -to_obs_x
                    
                    # Apply boost in this perpendicular direction
                    self.vx += perp_x * self.velocity_boost_strength
                    self.vy += perp_y * self.velocity_boost_strength
                    print(f"Perpendicular boost (right of obstacle): ({perp_x * self.velocity_boost_strength:.2f}, {perp_y * self.velocity_boost_strength:.2f})")
            
            # Check if duration expired
            if self.weakening_timer >= self.weakening_duration:
                self.weakening_active = False
                self.stuck_timer = 0.0
                self.is_stuck = False
                print("!!! [Virtual Force] DEACTIVATED")
        
        # Apply damping to simulate friction/air resistance
        self.vx *= self.damping
        self.vy *= self.damping
        
        # Limit to max speed
        speed = math.hypot(self.vx, self.vy)
        if speed > self.max_speed:
            self.vx = (self.vx / speed) * self.max_speed
            self.vy = (self.vy / speed) * self.max_speed
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Keep player on screen (optional boundary)
        self.x = max(self.width // 2, min(SCREEN_WIDTH - self.width // 2, self.x))
        self.y = max(self.height // 2, min(SCREEN_HEIGHT - self.height // 2, self.y))
        
        # Update rect for drawing and collision
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)

    def follow_course(self, course, course_is_closed):
        """Legacy method - keeping for compatibility but not used with field-based movement"""
        pass

    def draw(self, screen):
        """Draw the player on screen"""
        # Draw player as circle - orange if stuck, black otherwise
        player_color = (255, 165, 0) if self.is_stuck else BLACK
        pygame.draw.circle(screen, player_color, (int(self.x), int(self.y)), self.width // 2)
        
        # Draw velocity vector (optional - helpful for debugging)
        if abs(self.vx) > 0.1 or abs(self.vy) > 0.1:
            end_x = int(self.x + self.vx * 5)
            end_y = int(self.y + self.vy * 5)
            pygame.draw.line(screen, (255, 0, 0), (int(self.x), int(self.y)), (end_x, end_y), 2)
        
        # Draw indicator when weakening is active
        if self.weakening_active:
            # Purple circle to show weakening is active
            pygame.draw.circle(screen, (255, 0, 255), (int(self.x), int(self.y)), 
                             self.width // 2 + 5, 2)