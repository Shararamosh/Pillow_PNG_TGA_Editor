# Unreal Engine Import Texture Converter
A Python-written tool for batch conversion of images from any format supported by [PIL (Pillow)](https://pillow.readthedocs.io/en/stable/) library to RLE TGA or PNG depending on whether image has transparency or not.

Requirements:
- [Pillow](https://pypi.org/project/pillow/)
- [tqdm](https://pypi.org/project/tqdm/)
- [i18nice[YAML]](https://pypi.org/project/i18nice/)

This tool was mainly written for Unreal Engine 3/A Hat in Time Editor. PNG is (IMHO) the best image import format for this engine, however transparent images have alpha channel issues when imported. In this case it's best to use TGA format (more specifically RLE-compressed TGA).

This repo also includes the following tools to work with Pokémon Sword/Shield textures:
- ## Image X-axis Mirror+Concat
A tool for appending mirrored image to original one. After that, texture is no longer required to have Mirror wrap mode.
- ## Eyes/Mouth Texture Splitter
A tool for splitting eyes or mouth textures into sub-textures containing only a single pair of eyes or mouth. Useful when you don't want to deal with animated UVs in materials and instead use texture as parameter.