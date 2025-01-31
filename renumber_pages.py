import re

def replace_pattern_in_markdown(input_file, output_file):
    try:
        # Read the contents of the markdown file
        with open(input_file, 'r') as file:
            content = file.read()

        # Define the regex pattern to find {number}
        pattern = r"\{(\d+)\}"

        # Define the replacement function
        def replacement_function(match):
            number = int(match.group(1))
            return f"{{page : {number}}}"   #perform whatever add or subtract operation you want to do here

        # Replace all matches in the content
        updated_content = re.sub(pattern, replacement_function, content)

        # Write the updated content to the output file
        with open(output_file, 'w') as file:
            file.write(updated_content)

        print(f"Successfully updated the file. The output is saved in '{output_file}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

# Input and output file paths
input_file = "/home/technoidentity/LightRAG/testManual--paginate.md"
output_file = "csr_phi_compatible.md"

# Call the function to perform the replacement
replace_pattern_in_markdown(input_file, output_file)
