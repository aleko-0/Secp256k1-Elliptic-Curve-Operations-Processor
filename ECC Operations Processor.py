from sympy import mod_inverse as sympy_mod_inverse
from sympy.ntheory.residue_ntheory import nthroot_mod
import math

# Secp256k1 curve parameters
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a = 0x0000000000000000000000000000000000000000000000000000000000000000
b = 0x0000000000000000000000000000000000000000000000000000000000000007
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

# Base point G
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)

def mod_inverse(k, p):
    return pow(k, p-2, p)

def point_add(P, Q, p, a):
    if P is None: return Q
    if Q is None: return P
    
    x1, y1 = P
    x2, y2 = Q
    
    if x1 == x2:
        if y1 != y2: return None
        m = (3 * x1 * x1 + a) * mod_inverse(2 * y1, p) % p
    else:
        m = (y2 - y1) * mod_inverse(x2 - x1, p) % p
    
    x3 = (m*m - x1 - x2) % p
    y3 = (m*(x1 - x3) - y1) % p
    return (x3, y3)

def point_mul(k, point, p, a):
    result = None
    current = point
    while k > 0:
        if k % 2: result = point_add(result, current, p, a)
        current = point_add(current, current, p, a)
        k = k // 2
    return result

def format_hex(val, max_len=64):
    hex_str = f"{abs(val):0{max_len}x}"
    if len(hex_str) > max_len:
        return f"{hex_str[:max_len]}..."
    return hex_str

def is_point_on_curve(point, p, a, b):
    if point is None:
        return True
    x, y = point
    return (pow(y, 2, p) == (pow(x, 3, p) + a * x + b) % p)

class ECCProcessor:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.current_point = G
        self.current_privkey = 1  # privkey for G is 1
        self.history = []
    
    def apply_operation(self, operation, value):
        try:
            if operation in ('mul', 'div'):
                if self.current_privkey is None:
                    raise ValueError("Cannot perform operation: private key unknown (after addition/subtraction)")
                scalar = int(value, 16)
                
                if operation == 'mul':
                    new_privkey = (self.current_privkey * scalar) % n
                    new_point = point_mul(scalar, self.current_point, p, a)
                else:
                    if math.gcd(scalar, n) != 1:
                        raise ValueError("Divisor must be coprime with n")
                    inv = mod_inverse(scalar, n)
                    new_privkey = (self.current_privkey * inv) % n
                    new_point = point_mul(inv, self.current_point, p, a)
                
                self.history.append((operation, scalar))
                self.current_privkey = new_privkey
                self.current_point = new_point
                return True
                
            elif operation in ('add', 'sub'):
                x, y = value
                if operation == 'sub':
                    y = (-y) % p
                Q = (x, y)
                if not is_point_on_curve(Q, p, a, b):
                    raise ValueError("Point not on curve")
                new_point = point_add(self.current_point, Q, p, a)
                if new_point is None:
                    raise ValueError("Operation result is infinity")
                self.current_point = new_point
                self.current_privkey = None
                self.history.append((operation, (x, y)))
                return True
                
            else:
                raise ValueError("Invalid operation")
                
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def print_state(self):
        print("\nCurrent state:")
        if self.current_privkey is not None:
            print(f"Private key: 0x{format_hex(self.current_privkey)}")
        else:
            print("Private key: unknown (after addition/subtraction operations)")
        
        if self.current_point is None:
            print("Current point: Infinity")
            return
        
        x, y = self.current_point
        print(f"Current point:")
        print(f"x: 0x{format_hex(x)}")
        print(f"y: 0x{format_hex(y)}")
        print(f"-y: 0x{format_hex((-y) % p)}")
        
        try:
            x_roots = nthroot_mod((y*y - b) % p, 3, p, all_roots=True)
            print("\nPossible x-coordinates:")
            for i, root in enumerate(x_roots, 1):
                print(f"x{i}: 0x{format_hex(root)}")
        except Exception as e:
            print(f"\nError calculating x-coordinates: {e}")
    
    def show_history(self):
        print("\nOperation history:")
        for op, val in self.history:
            if op in ('add', 'sub'):
                x, y = val
                x_str = format_hex(x)
                y_str = format_hex(y)
                print(f"{op.upper()} point (x: 0x{x_str}, y: 0x{y_str})")
            else:
                print(f"{op.upper()} 0x{format_hex(val)}")

def main_menu():
    processor = ECCProcessor()
    
    while True:
        print("\n" + "="*50)
        print("Choose an action:")
        print("1 - Multiply current point")
        print("2 - Divide current point")
        print("3 - Reset to base point G")
        print("4 - Show operation history")
        print("5 - Add point")
        print("6 - Subtract point")
        print("7 - Exit")
        
        choice = input("Your choice: ").strip()
        
        if choice == '1':
            value = input("Enter multiplier (hex): ").strip()
            if processor.apply_operation('mul', value):
                processor.print_state()
        
        elif choice == '2':
            value = input("Enter divisor (hex): ").strip()
            if processor.apply_operation('div', value):
                processor.print_state()
        
        elif choice == '3':
            processor.reset()
            print("\nReset to base point G completed")
            processor.print_state()
        
        elif choice == '4':
            processor.show_history()
        
        elif choice == '5':
            value_x = input("Enter point's x-coordinate (hex): ").strip()
            value_y = input("Enter point's y-coordinate (hex): ").strip()
            try:
                x = int(value_x, 16)
                y = int(value_y, 16)
                if not is_point_on_curve((x, y), p, a, b):
                    print("Error: Point is not on the curve.")
                else:
                    if processor.apply_operation('add', (x, y)):
                        processor.print_state()
            except ValueError:
                print("Invalid coordinate input.")
        
        elif choice == '6':
            value_x = input("Enter point's x-coordinate (hex): ").strip()
            value_y = input("Enter point's y-coordinate (hex): ").strip()
            try:
                x = int(value_x, 16)
                y = int(value_y, 16)
                if not is_point_on_curve((x, y), p, a, b):
                    print("Error: Point is not on the curve.")
                else:
                    if processor.apply_operation('sub', (x, y)):
                        processor.print_state()
            except ValueError:
                print("Invalid coordinate input.")
        
        elif choice == '7':
            print("Exiting program")
            break
        
        else:
            print("Invalid choice")

if __name__ == "__main__":
    print("Advanced Elliptic Curve Operations Processor")
    print("Initial base point G:")
    print(f"x: 0x{format_hex(G[0])}")
    print(f"y: 0x{format_hex(G[1])}")
    main_menu()
