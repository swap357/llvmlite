import lief
import pathlib
import argparse
import subprocess
import tempfile
import os
import sys

def get_dll_imports(dll_path):
    """Extract imports from a DLL file."""
    try:
        dll = lief.PE.parse(str(dll_path))
        imports = set()
        delay_imports = set()
        
        if hasattr(dll, "delay_imports"):
            delay_imports = {x.name for x in dll.delay_imports}
        
        imports = {x.name for x in dll.imports}
        
        return imports, delay_imports
    except Exception as e:
        print(f"Error analyzing DLL {dll_path}: {str(e)}")
        return set(), set()

def unpack_wheel(wheel_path, output_dir):
    """Unpack a wheel file to the specified directory."""
    try:
        subprocess.run(["wheel", "unpack", wheel_path, "-d", output_dir], check=True, capture_output=True, text=True)
        return output_dir
    except subprocess.CalledProcessError as e:
        print(f"Error unpacking wheel {wheel_path}: {e.stderr}")
        raise

def find_dll_in_wheel(wheel_dir):
    """Find the llvmlite.dll in the unpacked wheel directory."""
    dll_path = None
    print(f"Searching for llvmlite.dll in {wheel_dir}")
    for path in pathlib.Path(wheel_dir).rglob("**/*.dll"):
        print(f"Found DLL: {path}")
        if path.name.lower() == "llvmlite.dll":
            dll_path = path
            print(f"Found llvmlite.dll at: {dll_path}")
            break
    if not dll_path:
        raise FileNotFoundError(f"Could not find llvmlite.dll in {wheel_dir}")
    return dll_path

def compare_wheels(wheel1_path, wheel2_path):
    """Compare DLLs between two wheel files."""
    print(f"\nComparing wheels:")
    print(f"Wheel 1: {wheel1_path}")
    print(f"Wheel 2: {wheel2_path}")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Unpack both wheels
            wheel1_dir = unpack_wheel(wheel1_path, os.path.join(temp_dir, "wheel1"))
            wheel2_dir = unpack_wheel(wheel2_path, os.path.join(temp_dir, "wheel2"))
            
            # Find DLLs
            dll1_path = find_dll_in_wheel(wheel1_dir)
            dll2_path = find_dll_in_wheel(wheel2_dir)
            
            # Get imports
            imports1, delay_imports1 = get_dll_imports(dll1_path)
            imports2, delay_imports2 = get_dll_imports(dll2_path)
            
            # Compare and report
            print("\nRegular imports comparison:")
            added_imports = imports2 - imports1
            removed_imports = imports1 - imports2
            if added_imports:
                print(f"Added imports: {sorted(added_imports)}")
            if removed_imports:
                print(f"Removed imports: {sorted(removed_imports)}")
            if not (added_imports or removed_imports):
                print("No changes in regular imports")
                
            print("\nDelay imports comparison:")
            added_delay = delay_imports2 - delay_imports1
            removed_delay = delay_imports1 - delay_imports2
            if added_delay:
                print(f"Added delay imports: {sorted(added_delay)}")
            if removed_delay:
                print(f"Removed delay imports: {sorted(removed_delay)}")
            if not (added_delay or removed_delay):
                print("No changes in delay imports")
            
            # Return True if there are no changes
            return not (added_imports or removed_imports or added_delay or removed_delay)
    except Exception as e:
        print(f"Error during wheel comparison: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Compare DLLs between two wheel files')
    parser.add_argument('wheel1', help='Path to first wheel file')
    parser.add_argument('wheel2', help='Path to second wheel file')
    args = parser.parse_args()
    
    if not os.path.exists(args.wheel1):
        print(f"Error: Wheel file {args.wheel1} does not exist")
        sys.exit(1)
    if not os.path.exists(args.wheel2):
        print(f"Error: Wheel file {args.wheel2} does not exist")
        sys.exit(1)
    
    if not compare_wheels(args.wheel1, args.wheel2):
        print("\nWARNING: DLL imports have changed between wheels!")
        sys.exit(1)
    else:
        print("\nNo changes detected in DLL imports.")

if __name__ == "__main__":
    main() 