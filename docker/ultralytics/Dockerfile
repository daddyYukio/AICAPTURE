FROM ultralytics/ultralytics:8.3.68-arm64

WORKDIR /work

RUN python -m pip install --upgrade pip
RUN pip install --upgrade packaging

RUN pip install --break-system-packages ncnn
RUN pip install --break-system-packages lap

COPY ./pnnx-20241223-linux-aarch64/pnnx /ultralytics/ultralytics

# Install dotnet runtime
RUN wget https://builds.dotnet.microsoft.com/dotnet/Runtime/9.0.9/dotnet-runtime-9.0.9-linux-arm64.tar.gz
RUN mkdir -p /opt/dotnet
RUN tar -zxf dotnet-runtime-9.0.9-linux-arm64.tar.gz -C /opt/dotnet
RUN rm dotnet-runtime-9.0.9-linux-arm64.tar.gz

# Create dummy aicap.sh and synbolic link
# Mount a host's aicap directory using -v when starting (the container).
RUN mkdir -p /usr/local/aicap/script/cap
RUN touch /usr/local/aicap/script/cap/aicap.sh
RUN ln -s /usr/local/aicap/script/cap/aicap.sh /usr/local/bin/aicap 

ENTRYPOINT ["python3"]


