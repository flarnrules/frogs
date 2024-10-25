# Frogs Art Engine
Welcome to the Frogs Art Engine.

## Quick start
If you have python3 installed, and you also have a bunch of libraries installed, you can just run `python3 generate_nfts.py` in the root directory.

If you don't have all that, you'll need to install Python3 and a bunch of libraries.

## What is the Frogs Art Engine
It is a python based image generator. It works best with square shaped images, and it can be used as the building blocks for an nft project, or other project where you want to generate some images using layers. 

The following collections have been created with this engine:

- frogs (on Stargaze)
- frog day (on Stargaze)
- Shitmos NFT (on Stargaze)

The following collections have been created from assets from those collections:

The following collections are in process:

- Puppy Cerberus
- Cosmic Gumball Machine
- Unnamed Unicorn Project

## How does the Frogs Art Engine Work?


### Basic file structure of the 'media' subdirectory
```php

media/
├── layers/
│   ├── core_layers/                   # Main sequence of layers
│   │   ├── background/
│   │   │   ├── background_1.png
│   │   │   └── background_2.png
│   │   ├── character/
│   │   │   ├── character_1.png
│   │   │   └── character_2.png
│   │   ├── object/
│   │   │   ├── object_1.png
│   │   │   └── object_2.png
│   │   └── other_core_layer_folders/
│   
│   ├── character_layers/               # Character-specific layers
│   │   ├── character_1/
│   │   │   ├── accessory/
│   │   │   │   ├── accessory_1.png
│   │   │   │   └── accessory_2.png
│   │   │   └── feature/
│   │   │       ├── feature_1.png
│   │   │       └── feature_2.png
│   │   ├── character_2/
│   │   │   ├── accessory/
│   │   │   └── feature/
│   
│   ├── frames/                         # Frames for picture frames
│   │   ├── frame_1.png
│   │   └── frame_2.png
│   
│   ├── popins/                         # Pop-ins (could be character-specific)
│   │   ├── popin_1.png
│   │   └── popin_2.png
│   │   ├── character_1_popin.png       # Pop-in for a specific character
│   │   └── character_2_popin.png

```