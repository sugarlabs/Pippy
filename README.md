# Pippy

A simple Python programming activity that lets you create, edit, and run Python code.

Pippy includes example programs ranging from very simple (Hello World) to more complex (Pong, Sierpinski Carpet, etc.) 

You can also save your own Python programs within Pippy and export them as standalone Sugar activities.

## Code Llama Integration

Pippy now includes a built-in side pane that can analyze your code using a local [Code Llama](https://github.com/facebookresearch/codellama) instance through Ollama. This feature provides code suggestions, improvement ideas, and identifies potential issues in your code as you write it.

### Setting up Code Llama with Ollama

To use the Code Llama integration:

1. Install Ollama from https://ollama.ai/
2. Pull the Code Llama 7B Instruct model: `ollama pull codellama:7b-instruct`
3. Start the included server script
4. Launch Pippy and start coding - the side pane will automatically analyze your code

#### Quick Setup Guide

Here's how to get started with the Code Llama integration:

1. Install Ollama:
   - Visit https://ollama.ai/ and follow the installation instructions for your platform
   - Linux: `curl https://ollama.ai/install.sh | sh`
   - macOS: Download from the Ollama website
   - Windows: Download from the Ollama website

2. After installing Ollama, pull the Code Llama model:
   ```bash
   ollama pull codellama
   ```

3. Run the relay server from the Pippy directory:
   ```bash
   ./codellama_server.py
   ```

   You can also specify different parameters:
   ```bash
   ./codellama_server.py --model codellama:7b --port 8080
   ```

4. Launch Pippy and start coding!

#### Using a Different Model

If you want to use a different model, you can pull it with Ollama and specify it when starting the server:

```bash
ollama pull codellama:7b-instruct
./codellama_server.py --model codellama:7b-instruct
```

For better performance and accuracy, consider these models:

1. **For speed (smaller models):**
   ```bash
   ollama pull codellama:7b-code
   ./codellama_server.py --model codellama:7b-code
   ```

2. **For better accuracy (larger models):**
   ```bash
   ollama pull deepseek-coder:6.7b
   ./codellama_server.py --model deepseek-coder:6.7b
   ```
   
3. **For the best balance of speed and accuracy:**
   ```bash
   ollama pull wizardcoder:7b-python
   ./codellama_server.py --model wizardcoder:7b-python
   ```

Other good models for code analysis:
- `codellama:7b`
- `codellama:13b` (slower but more accurate)
- `wizardcoder`
- `deepseek-coder`

## License Information

Pippy is licensed under the GPLv3.

How to use?
===========

Pippy is part of the Sugar desktop.  Please refer to;

* [How to Get Sugar on sugarlabs.org](https://sugarlabs.org/),
* [How to use Sugar](https://help.sugarlabs.org/),
* [How to use Pippy](https://help.sugarlabs.org/pippy.html).

How to upgrade?
===============

On Sugar desktop systems;
* use [My Settings](https://help.sugarlabs.org/my_settings.html), [Software Update](https://help.sugarlabs.org/my_settings.html#software-update).

How to integrate?
=================

On Debian and Ubuntu systems;

```
apt install sugar-pippy-activity
```

On Fedora systems;

```
dnf install sugar-pippy
```

Pippy depends on Python, [Sugar
Toolkit](https://github.com/sugarlabs/sugar-toolkit-gtk3), Cairo,
Telepathy, GTK+ 3,
[GtkSourceView](https://wiki.gnome.org/Projects/GtkSourceView), Pango,
Vte, Box2d and Pygame.

Pippy is started by [Sugar](https://github.com/sugarlabs/sugar).

Pippy is packaged by Linux distributions;
* [Fedora package sugar-pippy](https://src.fedoraproject.org/rpms/sugar-pippy)
* [Debian package sugar-pippy-activity](https://packages.debian.org/sugar-pippy-activity).

