import os

def is_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Try reading a small portion of the file
            file.read(1024)
        return True
    except (UnicodeDecodeError, IOError):
        return False

def get_file_sizes(start_path):
    file_sizes = []
    for root, dirs, files in os.walk(start_path):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                file_size = os.path.getsize(file_path)
                file_sizes.append((file_path, file_size))
    return file_sizes

def main():
    start_path = '.'  # Current directory
    file_sizes = get_file_sizes(start_path)
    file_sizes.sort(key=lambda x: x[1], reverse=False)  # Sort by size, smallest first

    total_cumulative_size = 0
    cumulative_size_by_extension = {}
    for file_path, size in file_sizes:
        if size != 0 and not file_path.startswith('./node_modules'):
            if is_text_file(file_path):
                total_cumulative_size += size
                extension = os.path.splitext(file_path)[1]
                cumulative_size_by_extension[extension] = cumulative_size_by_extension.get(extension, 0) + size
                print(f"{file_path} - {size} bytes (Cumulative Size: {total_cumulative_size} bytes)")

    # Sort and print cumulative size by file extension
    sorted_extensions = sorted(cumulative_size_by_extension.items(), key=lambda x: x[1])

    print("\nCumulative Size by File Extension (Smallest to Largest):")
    for extension, size in sorted_extensions:
        percentage = (size / total_cumulative_size) * 100 if total_cumulative_size else 0
        print(f"{extension if extension else 'No Extension'}: {size} bytes ({percentage:.2f}%)")

if __name__ == "__main__":
    main()
