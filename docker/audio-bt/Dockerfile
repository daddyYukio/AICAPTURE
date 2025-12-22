#
# An image with audio output and a Bluetooth module added to the base image
#
FROM aicap/arm64/ultralytics:1.0.250923

# install modules for audio 
RUN apt update && apt install -y alsa-utils libasound2 libportaudio2 libsndfile1
RUN pip install  --break-system-packages sounddevice soundfile numpy

# install bleak for accessing bluetooth device
RUN pip install  --break-system-packages bleak

