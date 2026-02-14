# field.py
import math

class Field:
    @staticmethod
    def calculate_attractive_force(position, goal, strength=1.0, max_distance=None, weakening_factor=1.0):
        """Calculate attractive force towards a goal"""
        dx = goal[0] - position[0]
        dy = goal[1] - position[1]
        distance = math.hypot(dx, dy)
        
        if distance == 0:
            return (0, 0)
        
        # Normalize direction
        direction_x = dx / distance
        direction_y = dy / distance
        
        # Linear attraction (could also use quadratic: strength * distance)
        force_magnitude = strength * weakening_factor  # Apply weakening factor
        
        # Optional: cap the force at max_distance
        if max_distance and distance > max_distance:
            force_magnitude *= (max_distance / distance)
        
        return (direction_x * force_magnitude, direction_y * force_magnitude)
    
    @staticmethod
    def calculate_repulsive_force(position, obstacle_center, obstacle_radius, 
                                   strength=100.0, influence_distance=150.0):
        """Calculate repulsive force from an obstacle"""
        dx = position[0] - obstacle_center[0]
        dy = position[1] - obstacle_center[1]
        distance = math.hypot(dx, dy)
        
        # Distance from edge of obstacle
        edge_distance = distance - obstacle_radius
        
        if edge_distance <= 0:
            # Inside obstacle - strong repulsion
            if distance == 0:
                return (0, 0)
            direction_x = dx / distance
            direction_y = dy / distance
            return (direction_x * strength * 10, direction_y * strength * 10)
        
        if edge_distance > influence_distance:
            # Too far away - no influence
            return (0, 0)
        
        # Normalize direction (away from obstacle)
        direction_x = dx / distance
        direction_y = dy / distance
        
        # Inverse square law for repulsion (1/d^2)
        force_magnitude = strength / (edge_distance ** 2)
        
        return (direction_x * force_magnitude, direction_y * force_magnitude)
    
    @staticmethod
    def calculate_repulsive_force_rect(position, rect, strength=100.0, influence_distance=150.0):
        """Calculate repulsive force from a rectangular obstacle"""
        px, py = position
        
        # Find closest point on rectangle to the position
        closest_x = max(rect.left, min(px, rect.right))
        closest_y = max(rect.top, min(py, rect.bottom))
        
        # Vector from closest point to position
        dx = px - closest_x
        dy = py - closest_y
        distance = math.hypot(dx, dy)
        
        if distance == 0:
            # Position is inside rectangle - push out from center
            dx = px - rect.centerx
            dy = py - rect.centery
            distance = math.hypot(dx, dy)
            if distance == 0:
                return (0, 0)
            direction_x = dx / distance
            direction_y = dy / distance
            return (direction_x * strength * 10, direction_y * strength * 10)
        
        if distance > influence_distance:
            # Too far away - no influence
            return (0, 0)
        
        # Normalize direction (away from obstacle)
        direction_x = dx / distance
        direction_y = dy / distance
        
        # Inverse square law for repulsion (1/d^2)
        force_magnitude = strength / (distance ** 2)
        
        return (direction_x * force_magnitude, direction_y * force_magnitude)
    
    @staticmethod
    def calculate_min_safety(position, direction, obstacles, max_range=200):
        """
        Calculate minimum safety (minS) - the safety metric for the intended direction.
        Now also considers obstacles that are very close, regardless of direction.
        
        Args:
            position: Current position (x, y)
            direction: Intended movement direction (dirX, dirY) - should be normalized
            obstacles: List of obstacle objects
            max_range: Maximum distance to check
            
        Returns:
            minS: Minimum safety value (lower = more dangerous)
        """
        minS = max_range  # Start with maximum (200)
        px, py = position
        dirX, dirY = direction
        
        # Normalize direction if needed
        dir_magnitude = math.hypot(dirX, dirY)
        if dir_magnitude > 0:
            dirX /= dir_magnitude
            dirY /= dir_magnitude
        else:
            return minS
        
        for obstacle in obstacles:
            # Calculate distance to obstacle
            if hasattr(obstacle, 'is_trap') and obstacle.is_trap:
                # For rectangular obstacles, find distance to nearest edge
                closest_x = max(obstacle.rect.left, min(px, obstacle.rect.right))
                closest_y = max(obstacle.rect.top, min(py, obstacle.rect.bottom))
                dx_to_edge = px - closest_x
                dy_to_edge = py - closest_y
                dist_to_obstacle = math.hypot(dx_to_edge, dy_to_edge)
            else:
                # For circular obstacles
                dx_to_center = obstacle.rect.centerx - px
                dy_to_center = obstacle.rect.centery - py
                dist_to_center = math.hypot(dx_to_center, dy_to_center)
                dist_to_obstacle = dist_to_center - (obstacle.width / 2)
            
            # PROXIMITY CHECK: If very close to obstacle, set low safety regardless of direction
            proximity_threshold = 30  # pixels
            if dist_to_obstacle < proximity_threshold:
                # Very close obstacle - calculate reduced safety based on proximity
                proximity_safety = max(1.0, dist_to_obstacle)  # Minimum 1 to avoid zero
                if proximity_safety < minS:
                    minS = proximity_safety
                    print(f"  Close obstacle detected! Distance: {dist_to_obstacle:.1f}px, safety: {proximity_safety:.1f}")
                continue  # Skip directional check for very close obstacles
            
            # DIRECTIONAL CHECK: For obstacles further away, check if they're in our path
            dx = obstacle.rect.centerx - px
            dy = obstacle.rect.centery - py
            distSq = dx * dx + dy * dy
            
            # Skip very close to center (avoid division by zero)
            if distSq < 1:
                minS = 1.0
                continue
            
            # Calculate dot product (projection onto movement direction)
            dot_product = dx * dirX + dy * dirY
            
            # Skip obstacles behind us
            if dot_product <= 0:
                continue
            
            # Safety metric: distance² / projection
            # This represents "how far until we hit this obstacle in our current direction"
            safety = distSq / dot_product
            
            # Update minimum safety
            if safety > 0 and safety < minS:
                minS = safety
        
        return minS