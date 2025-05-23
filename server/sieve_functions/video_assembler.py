import sieve
import os
import tempfile

# Fix for MoviePy compatibility with newer Pillow versions
try:
    from PIL import Image
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# MoviePy version-agnostic imports
try:
    # Try MoviePy v2.0+ imports (no .editor)
    from moviepy import VideoFileClip, clips_array
except ImportError:
    # Fallback to MoviePy v1.x imports (with .editor)
    from moviepy.editor import VideoFileClip, clips_array


def resize_and_pad(clip, target_w, target_h):
    """Resizes a clip to fit target dimensions, maintaining aspect ratio and centering."""
    try:
        print(f"  Resizing clip from {clip.w}x{clip.h} to {target_w}x{target_h}")
        
        # Calculate scaling factors for width and height
        scale_w = target_w / clip.w
        scale_h = target_h / clip.h
        
        # Use the smaller scale factor to maintain aspect ratio and fit within bounds
        scale_factor = min(scale_w, scale_h)
        
        # Calculate new dimensions
        new_w = int(clip.w * scale_factor)
        new_h = int(clip.h * scale_factor)
        
        print(f"  Scale factor: {scale_factor:.3f}, new size: {new_w}x{new_h}")
        
        # Resize the clip
        resized_clip = clip.resize(width=new_w, height=new_h)
        
        # Calculate padding needed to center the clip
        padding_w = target_w - new_w
        padding_h = target_h - new_h
        left_pad = padding_w // 2
        right_pad = padding_w - left_pad
        top_pad = padding_h // 2
        bottom_pad = padding_h - top_pad
        
        print(f"  Padding - width: {padding_w}px (L:{left_pad}, R:{right_pad}), height: {padding_h}px (T:{top_pad}, B:{bottom_pad})")
        
        # Apply padding if needed
        if padding_w > 0 or padding_h > 0:
            padded_clip = resized_clip.margin(
                left=left_pad, 
                right=right_pad, 
                top=top_pad, 
                bottom=bottom_pad, 
                color=(0,0,0)
            )
        else:
            padded_clip = resized_clip
            
        print(f"  Final clip size: {padded_clip.w}x{padded_clip.h}")
        return padded_clip
        
    except Exception as e:
        print(f"  Error in resize_and_pad: {e}")
        print(f"  Input clip info: size={clip.w}x{clip.h}, duration={clip.duration}")
        raise


@sieve.function(
    name="spew_video_assembler",
    python_packages=["moviepy", "Pillow"],
    system_packages=["ffmpeg"]
)
def assemble_final_video(celebrity_video: sieve.File, visuals_video: sieve.File) -> sieve.File:
    """
    Assembles the final video by stacking the visuals video on top of the 
    celebrity video, creating a mobile-friendly vertical video (1080x2160).
    
    Args:
        celebrity_video: Sieve.File object of the celebrity video (with audio)
        visuals_video: Sieve.File object of the visuals video
        
    Returns:
        sieve.File: The assembled final video
    """
    print(f"Assembling mobile-friendly vertical video from celebrity and visuals videos")
    celeb_clip = None
    visuals_clip = None
    final_clip = None

    try:
        # Create temporary directory for processing (don't auto-cleanup)
        temp_dir = tempfile.mkdtemp()
        final_path = os.path.join(temp_dir, 'final_video.mp4')

        # Mobile-friendly vertical dimensions (9:16 aspect ratio)
        clip_w = 1080  # Each clip width
        clip_h = 1080  # Each clip height (square clips)
        target_w = 1080  # Final video width
        target_h = 2160  # Final video height (2 x 1080)

        # Load clips from Sieve File objects
        print("Loading video clips...")
        print(f"  Celebrity video path: {celebrity_video.path}")
        print(f"  Visuals video path: {visuals_video.path}")
        
        celeb_clip = VideoFileClip(celebrity_video.path)
        visuals_clip = VideoFileClip(visuals_video.path)
        
        print(f"  Celebrity clip: {celeb_clip.w}x{celeb_clip.h}, duration: {celeb_clip.duration}s")
        print(f"  Visuals clip: {visuals_clip.w}x{visuals_clip.h}, duration: {visuals_clip.duration}s")
        print("Clips loaded.")

        # Use celebrity video's duration as the master duration
        master_duration = celeb_clip.duration
        print(f"Using master duration: {master_duration}s")
        
        # Resize and pad clips to 1080x1080, using master duration
        print("Resizing and padding clips to 1080x1080...")
        print("Processing celebrity clip...")
        celeb_processed = resize_and_pad(celeb_clip, clip_w, clip_h).set_duration(master_duration)
        print("Processing visuals clip...")
        visuals_processed = resize_and_pad(visuals_clip, clip_w, clip_h).set_duration(master_duration)
        print("Clips processed.")

        # Stack the clips vertically (visuals on top)
        print("Stacking clips...")
        final_clip = clips_array([[visuals_processed], [celeb_processed]])
        print(f"Final stacked clip: {final_clip.w}x{final_clip.h}")
        
        # Set the audio from the celebrity clip
        if celeb_clip.audio:
            print("Setting audio...")
            final_clip = final_clip.set_audio(celeb_clip.audio)
        else:
             print("Warning: Celebrity clip has no audio.")

        # Write the final video
        print(f"Writing final video to: {final_path}...")
        final_clip.write_videofile(
            final_path, 
            codec='libx264', 
            audio_codec='aac',
            threads=4, # Use multiple threads for faster encoding
            logger='bar' # Show progress bar
        )
        print("Final video written successfully.")
        
        # Verify the file exists before returning
        if os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"Final video file size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
            
            # Return as Sieve File object
            return sieve.File(path=final_path)
        else:
            raise FileNotFoundError(f"Final video was not created at {final_path}")

    except Exception as e:
        print(f"Error assembling video: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise # Re-raise the exception to signal failure in the Sieve function

    finally:
        # Clean up resources
        print("Cleaning up video resources...")
        if celeb_clip:
            try:
                celeb_clip.close()
            except Exception as e:
                 print(f"Error closing celeb_clip: {e}")
        if visuals_clip:
             try:
                visuals_clip.close()
             except Exception as e:
                 print(f"Error closing visuals_clip: {e}")
        # Intermediate clips (processed) are usually handled by final_clip closure
        if final_clip:
            try:
                final_clip.close()
            except Exception as e:
                 print(f"Error closing final_clip: {e}")
        print("Cleanup complete.")
