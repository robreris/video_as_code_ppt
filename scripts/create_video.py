import os
import subprocess
import shutil
import argparse

# Bake in parser
parser = argparse.ArgumentParser()
parser.add_argument("--output-name", default="final_output", help="Output video filename (without extension)")
args = parser.parse_args()

# Define directories
image_dir = "assets/images"
audio_dir = "assets/audio"
output_dir = "assets/temp"
output_final_dir = "outputs"
bumper_path_in = os.path.abspath("assets/bumpers/bumper_in.mp4")  # Absolute path to bumper video
bumper_path_out = os.path.abspath("assets/bumpers/bumper_out.mp4")  # Absolute path to bumper video

final_output = os.path.join(output_final_dir, f"{args.output_name}.mp4")

# Create output and temp directories if they don't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

if not os.path.exists(output_final_dir):
    os.makedirs(output_final_dir)

# Function to get the duration of an audio file using ffprobe
def get_audio_duration(audio_path):
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', audio_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    return float(result.stdout)

# Function to check if an audio file is already CBR
def is_cbr(audio_file):
    ffprobe_command = [
        'ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 
        'format=bit_rate', '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]
    result = subprocess.run(ffprobe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bitrate_info = result.stdout.decode('utf-8').strip()

    if bitrate_info:
        print(f"{audio_file} is CBR with bit rate {bitrate_info}")
        return True
    else:
        print(f"{audio_file} is VBR or could not detect bit rate.")
        return False

# Function to convert audio to CBR if needed
def convert_to_cbr(input_audio, output_audio):
    if is_cbr(input_audio):
        print(f"Skipping conversion for {input_audio}, already CBR.")
    else:
        cbr_command = [
            'ffmpeg', '-i', input_audio, '-b:a', '192k', '-ar', '48000', '-ac', '2', '-y', output_audio
        ]
        print(f"Converting {input_audio} to CBR: {output_audio}")
        subprocess.run(cbr_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Get list of image and audio files
images = sorted([f for f in os.listdir(image_dir) if f.endswith(('.png', '.jpg', '.jpeg'))])
audios = sorted([f for f in os.listdir(audio_dir) if f.endswith(('.mp3', '.wav'))])

# Generate video for each image/audio pair using ffmpeg
for idx, (image, audio) in enumerate(zip(images, audios)):
    image_path = os.path.join(image_dir, image)
    audio_path = os.path.join(audio_dir, audio)
    output_video = os.path.join(output_dir, f"output_{idx+1:03d}.mp4")

    # Get the duration of the audio file
    audio_duration = get_audio_duration(audio_path)

    # ffmpeg command to generate video for each image/audio pair
    ffmpeg_command = [
        'ffmpeg', '-y', '-i', image_path,  # No loop, just show image once
        '-i', audio_path,  # Audio plays only once
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Scale to even dimensions
        '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart',  # Ensure moov atom is written at the start
        '-t', str(audio_duration),  # Set video duration explicitly to audio duration
        output_video
    ]

    print(f"Creating video: {output_video}")
    process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(process.stdout.decode('utf-8'))
    print(process.stderr.decode('utf-8'))

    # Check if the output video was created successfully
    if not os.path.exists(output_video):
        print(f"Failed to create {output_video}, skipping this file.")
        continue

# Create file list for concatenation
filelist_path = os.path.join(output_dir, 'filelist.txt')
with open(filelist_path, 'w') as f:
    # Check if bumper exists and write it at the beginning
    if os.path.exists(bumper_path_in):
        print(f"Bumper found at {bumper_path_in}, adding to the beginning and end.")
        f.write(f"file '{bumper_path_in}'\n")  # Include the bumper at the beginning
    
    # Add the generated videos
    for idx in range(len(images)):
        video_file = f"output_{idx+1:03d}.mp4"  # Only the filename is needed
        video_file_path = os.path.abspath(os.path.join(output_dir, video_file))  # Absolute path
        if os.path.exists(video_file_path):
            f.write(f"file '{video_file_path}'\n")
        else:
            print(f"Warning: {video_file_path} not found, skipping.")

    # Add bumper.mp4 at the end
    if os.path.exists(bumper_path_out):
        f.write(f"file '{bumper_path_out}'\n")
    else:
        print(f"Bumper not found at {bumper_path_out}, skipping.")

# Print the filelist.txt content for debugging
print("\n--- filelist.txt content ---")
with open(filelist_path, 'r') as f:
    print(f.read())
print("--- End of filelist.txt ---\n")

# ffmpeg command to concatenate the videos with the overwrite flag (-y)
concat_command = [
    'ffmpeg', '-loglevel', 'verbose', '-y', '-f', 'concat', '-safe', '0', '-i', filelist_path, '-c', 'copy', final_output
]

print(f"Concatenating videos into: {final_output}")
concat_process = subprocess.run(concat_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Debugging: Print the output and error from ffmpeg
print(concat_process.stdout.decode('utf-8'))
print(concat_process.stderr.decode('utf-8'))

# Check if the final output was successfully created
if os.path.exists(final_output):
    print(f"{final_output} created successfully.")
    
    # Remove the output_dir (assets/temp) directory after final_output.mp4 is created
    try:
        shutil.rmtree(output_dir)
        print(f"Deleted the directory: {output_dir}")
    except Exception as e:
        print(f"Error deleting {output_dir}: {e}")
else:
    print(f"Failed to create {final_output}, skipping deletion of {output_dir}.")
