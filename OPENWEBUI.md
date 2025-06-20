# Connecting Open Web UI with Stable Diffusion

This guide explains how to connect Open Web UI (OpenWebUI) to the Stable Diffusion (AUTOMATIC1111) container for local image generation.

---

## Prerequisites

* Both containers (`open-webui` and `sdwebui`) must be running on the **same Docker network** (e.g., `everest`).
* Your Stable Diffusion container should expose port `7860` with the API enabled (`--api` in your CMD/entrypoint).
* Models are mounted and accessible at the expected path (see Docker Compose).
* Set the correct environment variables in the `open-webui` service.

---

## Example Docker Compose (OpenWebUI + Ollama + PostgreSQL)

```yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:${WEBUI_DOCKER_TAG}
    container_name: open-webui
    depends_on:
      - postgres
      - ollama
    ports:
      - "${OPEN_WEBUI_PORT}:8080"
    volumes:
      - open-webui-data:/app/backend/data
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - OLLAMA_BASE_URL=http://ollama:11434
      - WEBUI_ADMIN_EMAIL=${WEBUI_ADMIN_EMAIL}
      - WEBUI_ADMIN_PASSWORD=${WEBUI_ADMIN_PASSWORD}
      # --- For image generation via Stable Diffusion ---
      - AUTOMATIC1111_BASE_URL=http://sdwebui:7860/
      - ENABLE_IMAGE_GENERATION=true
      - IMAGE_GENERATION_MODEL=v1-5-pruned-emaonly
      - IMAGE_SIZE=640x800
    extra_hosts:
      - host.docker.internal:host-gateway
    networks:
      - everest
    restart: unless-stopped

  sd-webui:
    image: suhailphotos/sdwebui:cuda12.6-torch2.3-xf26
    container_name: sdwebui
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ${NEBULA_AI_MODELS}/sd-webui/models:/models/Stable-diffusion
      - ${NEBULA_AI_MODELS}/sd-webui/outputs:/outputs
    ports:
      - "7860:7860"
    networks:
      - everest
    restart: unless-stopped

networks:
  everest:
    external: true
```

---

## Required Environment Variables

For Open Web UI to recognize and use Stable Diffusion for image generation, set the following in the `open-webui` service:

```yaml
- AUTOMATIC1111_BASE_URL=http://sdwebui:7860/
- ENABLE_IMAGE_GENERATION=true
- IMAGE_GENERATION_MODEL=v1-5-pruned-emaonly
- IMAGE_SIZE=640x800
```

---

## Configuration Steps

1. **Ensure both containers are on the same Docker network** (`everest` in this example).
2. **Set environment variables** in your `docker-compose.yml` for OpenWebUI as shown above.
3. **Launch the containers** using `docker compose up -d`.

---

## Final Integration Step (UI Configuration)

Even with the right environment variables, you **must** select the image generation backend in the Open Web UI itself.

### 1. Open Web UI Settings

* Go to **Settings** (bottom left menu).
* Click **Admin Settings** if not already in admin mode.

[Open Web UI: General Settings Page](assets/openwebui_settings_page1.jpg)

---

### 2. Image Generation Settings

* Go to **Images** in the left sidebar under Settings.
* For **Image Generation Engine**, select `Automatic1111`.
* Set the **AUTOMATIC1111 Base URL** to `http://sdwebui:7860/`.
* Optionally configure sampler, scheduler, CFG scale, default model, image size, and steps as needed.

[Open Web UI: Image Generation Settings Page](assets/openwebui_settings_page4.jpg)

---

### 3. Select the Image Generation Provider

* Ensure `Automatic1111` is checked as your image generation provider.
* You can choose from multiple backends here if you have more than one configured.

[Selecting Image Generation Backend](assets/openwebui_settings_page4.jpg)

---

### 4. Verify and Test

* Once settings are saved, you should see Stable Diffusion models available for generation tasks in the OpenWebUI interface.
* Try generating an image to confirm the integration.

---

## Example Screenshots

* [General Settings – Admin View](assets/openwebui_settings_page1.jpg)
* [Main UI and Settings Menu](assets/openwebui_settings_page2.jpg)
* [Admin Settings: Enable/Configure Features](assets/openwebui_settings_page3.jpg)
* [Image Generation: Select Automatic1111 as Backend](assets/openwebui_settings_page4.jpg)

---

## Troubleshooting

* **Models not detected?**
  Check that the SD container is running, API is enabled, and the containers are on the same network.
* **Cannot generate images?**
  Double-check the Open Web UI backend selection in the UI (must be set to Automatic1111).
* **Model name mismatch?**
  The value for `IMAGE_GENERATION_MODEL` must match exactly the model title from `/sdapi/v1/sd-models` (use API or logs to confirm).

---

If you need to update the setup or add new models/backends, just repeat the above steps and update the relevant environment variables or UI settings.

---

**For more details on integrating OpenWebUI with Stable Diffusion, refer to the screenshots or reach out for assistance.**

