import os

# Specify the directory containing your files
directory = "../frog_day/nfts/images/"

# Loop through each file in the directory
for filename in os.listdir(directory):
    if filename.startswith("processed_"):
        # Generate the new filename by removing "preprocess_"
        new_filename = filename.replace("processed_", "")
        
        # Construct the full old and new file paths
        old_file = os.path.join(directory, filename)
        new_file = os.path.join(directory, new_filename)
        
        # Rename the file
        os.rename(old_file, new_file)

print("Files have been renamed.")
