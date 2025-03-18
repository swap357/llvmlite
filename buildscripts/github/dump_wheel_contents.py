import subprocess
import tempfile
import os
import argparse
import lief
from pathlib import Path
import platform

def get_dll_imports(dll_path):
    """Extract imports from a DLL file."""
    dll = lief.PE.parse(str(dll_path))
    imports = set()
    delay_imports = set()
    
    if hasattr(dll, "delay_imports"):
        delay_imports = {x.name for x in dll.delay_imports}
    
    imports = {x.name for x in dll.imports}
    
    return sorted(list(imports)), sorted(list(delay_imports))

def dump_wheel_contents(wheel_path, output_path):
    """Dump wheel contents using dir or tree command and analyze DLL imports."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Unpack the wheel
        subprocess.run(["wheel", "unpack", wheel_path, "-d", temp_dir], check=True)
        
        # Get the unpacked directory name
        wheel_dir = next(os.scandir(temp_dir)).path
        
        # Use dir on Windows, tree on Unix-like systems
        if platform.system() == 'Windows':
            cmd = ["cmd", "/c", "dir", "/s", "/b", wheel_dir]
        else:
            try:
                cmd = ["tree", "-h", "--noreport", "--charset=ascii", wheel_dir]
            except FileNotFoundError:
                cmd = ["ls", "-la", "-R", wheel_dir]
        
        # Run the command and capture output
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Write to file
        with open(output_path, 'w') as f:
            f.write(f"Contents of wheel: {os.path.basename(wheel_path)}\n")
            f.write("=" * 80 + "\n\n")
            f.write(result.stdout)
            
            # Add DLL imports section
            f.write("\n" + "=" * 80 + "\n")
            f.write("DLL Imports Analysis\n")
            f.write("=" * 80 + "\n\n")
            
            # Find and analyze all DLLs
            for dll_path in Path(wheel_dir).rglob("*.dll"):
                rel_path = dll_path.relative_to(wheel_dir)
                f.write(f"\nDLL: {rel_path}\n")
                f.write("-" * 40 + "\n")
                
                try:
                    imports, delay_imports = get_dll_imports(dll_path)
                    if imports:
                        f.write("Regular imports:\n")
                        for imp in imports:
                            f.write(f"  {imp}\n")
                    if delay_imports:
                        f.write("\nDelay imports:\n")
                        for imp in delay_imports:
                            f.write(f"  {imp}\n")
                except Exception as e:
                    f.write(f"Error analyzing DLL: {e}\n")
                f.write("\n")
        
        print(f"Wheel contents have been dumped to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Dump wheel contents to a text file')
    parser.add_argument('wheel_path', help='Path to the wheel file to analyze')
    parser.add_argument('--output', '-o', help='Output file path (default: wheel_contents.txt)',
                       default='wheel_contents.txt')
    args = parser.parse_args()
    
    dump_wheel_contents(args.wheel_path, args.output)

if __name__ == "__main__":
    main() 