import argparse
import os
import requests
import json
import fnmatch
import pathspec

def is_hidden(filepath):
    return os.path.basename(filepath).startswith('.')

def read_gitignore(directory):
    gitignore_path = os.path.join(directory, '.gitignore')
    if not os.path.exists(gitignore_path):
        return None
    with open(gitignore_path, 'r') as file:
        spec = pathspec.PathSpec.from_lines('gitwildmatch', file)
    return spec

def is_source_code(file):
    source_code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.ts', '.php', '.rb', '.go']
    _, ext = os.path.splitext(file)
    return ext in source_code_extensions

def process_directory(directory, model_name, api_url):
    responses = []
    gitignore_spec = read_gitignore(directory)
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not is_hidden(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            if is_source_code(file) and (not gitignore_spec or not gitignore_spec.match_file(file_path)):
                response = process_file(file_path, model_name, api_url)
                summary = "#Summary for " + file_path + ":\n" + response + "\n\n"
                responses.append(summary)
    return responses

def process_file(filepath, model_name, api_url):
    with open(filepath, 'r') as file:
        file_content = file.read()
    prompt = "summarize this code by identifying important functions and classes.  Ignore all helper functions, built in calls, and focus just on the most important code.  Conciseness matters. Here is the code:\n\n " + file_content
    print("prompt is ", prompt)
    response = requests.post(api_url, json={"model": model_name, "prompt": prompt}, stream=True)

    accumulated_response = ""
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            json_response = json.loads(decoded_line)
            print(json_response["response"], end=' ', flush=True)

            accumulated_response += json_response.get("response", "")

            if json_response.get("done", False):
                break

    return accumulated_response


def main():
    parser = argparse.ArgumentParser(description="Process files for summarization")
    parser.add_argument("file_or_directory", nargs='?', default=os.getcwd())
    parser.add_argument("--model", default="codellama:34b")
    parser.add_argument("--api_url", default="http://localhost:11434/api/generate") 
    parser.add_argument("--output", default="apispec.md")

    args = parser.parse_args()

    arg = args.file_or_directory
    #figure out if it is a file or directory
    if os.path.isdir(arg):
        directory = arg
        isDirectory = True
    elif os.path.isfile(arg):
        file = os.path.dirname(arg)
    else:
        print("Error: file or directory not found")
        return
    model_name = args.model
    api_url = args.api_url

    if isDirectory:
        responses = process_directory(directory, model_name, api_url)
    else:
        responses = process_file(file, model_name, api_url)
    print('responses are')
    print(responses)
    with open(args.output, 'w') as outfile:
        #responses is a string, just write it to the file
        #responses is an array, make it a string and write it to the file
        data = '\n'.join(responses)
        outfile.write(data)
        #json.dump(responses, outfile)

if __name__ == "__main__":
    main()
