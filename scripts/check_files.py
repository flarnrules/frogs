import os

def find_missing_files(directory_path, file_extension='.png'):
    # List all files in the directory
    all_files = os.listdir(directory_path)
    
    # Extract file numbers for files matching the expected extension
    file_numbers = {
        int(filename.split('.')[0]) for filename in all_files if filename.endswith(file_extension)
    }
    
    # Generate the expected set of file numbers
    expected_numbers = set(range(1, 4201))  # 4201 because range is exclusive at the end
    
    # Find the difference
    missing_numbers = expected_numbers - file_numbers
    
    return sorted(missing_numbers)

# Usage example:
directory_path = '../frog_day/nfts/images'
missing_files = find_missing_files(directory_path)
print("Missing files:", missing_files)