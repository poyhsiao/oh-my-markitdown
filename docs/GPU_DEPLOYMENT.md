# GPU Deployment Guide

## Prerequisites

- Linux server with NVIDIA GPU
- NVIDIA driver installed (`nvidia-smi` works)
- Docker + Docker Compose installed
- NVIDIA Container Toolkit installed

## Step 1: Install NVIDIA Container Toolkit

```bash
# Add NVIDIA repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Step 2: Verify GPU Access in Docker

```bash
# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Expected output: Your GPU info (name, memory, driver version).

## Step 3: Deploy with GPU Profile

```bash
# Build and start GPU-accelerated container
docker compose --profile gpu up -d markitdown-api-gpu

# Check logs
docker compose logs -f markitdown-api-gpu
```

## Step 4: Verify GPU Detection

```bash
# Check device info
curl http://localhost:51083/api/v1/device-info | python3 -m json.tool
```

Expected output:
```json
{
  "device": "cuda",
  "cuda_available": true,
  "cuda_device_name": "NVIDIA GeForce RTX 4090",
  "cuda_device_count": 1,
  "cuda_memory_gb": 24.0,
  "recommended_compute_type": "float16",
  "in_docker": true
}
```

## Step 5: Run Verification Script

```bash
# Copy verification script into container
docker cp scripts/verify_gpu_detection.py markitdown-api-gpu:/app/

# Run verification
docker exec markitdown-api-gpu python3 /app/verify_gpu_detection.py
```

Expected: 21/21 passed (including nvidia-smi detection).

## Step 6: Test Transcription

```bash
# Test with a YouTube video
curl -X POST "http://localhost:51083/api/v1/convert/youtube?url=YOUR_URL&language=zh&model_size=auto&return_format=markdown&quality_mode=fast" -o output.md

# Check logs for GPU usage
docker compose logs markitdown-api-gpu 2>&1 | grep -i "cuda\|gpu\|device"
```

Expected log:
```
NVIDIA GPU detected via nvidia-smi
[Whisper] Loading model: base (device=cuda, compute_type=float16, cpu_threads=0)
```

## Troubleshooting

### "nvidia-smi not found" in container
- Ensure `nvidia-container-toolkit` is installed
- Ensure Docker was restarted after configuration
- Check `docker compose --profile gpu` (not just `docker compose up`)

### "CUDA out of memory"
- Increase memory limit in `.env`: `MEMORY_LIMIT=16G`
- Use smaller model: `model_size=tiny` or `model_size=base`

### GPU not detected
- Run `nvidia-smi` on host to verify driver is working
- Check `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi`
