
# Usage:
### Install Requirements:
```
pip install -r requirements.txt
```

### download blender:
- windown: Download using this link
 https://mirror.freedif.org/blender/release/Blender4.4/blender-4.4.0-windows-x64.zip
- linux: enter this command in terminal
```
wget https://mirror.freedif.org/blender/release/Blender4.4/blender-4.4.0-linux-x64.tar.xz
```
**Download and extract the Blender folder into the Data_preprocessing folder.**

### Start Preprocessing:
Grant permissions: 
```
chmod +x run.sh
```
Run:
```
./run.sh /path/to/your/objects/forder/
```
**Objects folder format should look like this :**
```
/path/to/objects/
│   └── obj1/  
│   └── obj2/ 
```
