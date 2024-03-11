# become-image

Adapt any picture of a face into another image

Run this model on Replicate:

https://replicate.com/fofr/become-image

Or run it in ComfyUI:

https://github.com/fofr/cog-become-image/blob/main/become-image-ui.json

You’ll need these custom nodes:

- [ComfyUI Controlnet Aux](https://github.com/Fannovel16/comfyui_controlnet_aux/tree/6d6f63c)
- [ComfyUI InstantID](https://github.com/cubiq/ComfyUI_InstantID/tree/0fcf494)
- [ComfyUI IPAdapter Plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus/tree/4e898fe)
- [ComfyUI Essentials](https://github.com/cubiq/ComfyUI_essentials/tree/c9236fe)
- [Efficiency Nodes ComfyUI](https://github.com/jags111/efficiency-nodes-comfyui/tree/1ac5f18)

## Developing locally

Clone this repository:

```sh
git clone --recurse-submodules https://github.com/fofr/cog-become-image.git
```

Run the [following script](https://github.com/fofr/cog-become-image/blob/main/scripts/clone_plugins.sh) to install all the custom nodes:

```sh
./scripts/clone_plugins.sh
```

### Running the Web UI from your Cog container

1. **GPU Machine**: Start the Cog container and expose port 8188:
```sh
sudo cog run -p 8188 bash
```
Running this command starts up the Cog container and let's you access it

2. **Inside Cog Container**: Now that we have access to the Cog container, we start the server, binding to all network interfaces:
```sh
cd ComfyUI/
python main.py --listen 0.0.0.0
```

3. **Local Machine**: Access the server using the GPU machine's IP and the exposed port (8188):
`http://<gpu-machines-ip>:8188`

When you goto `http://<gpu-machines-ip>:8188` you'll see the classic ComfyUI web form!
