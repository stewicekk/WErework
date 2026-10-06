# WorldEditor-Renewal — verified reference analysis

Source: https://github.com/Debloat/WorldEditor-Renewal/tree/main/ClientSource/WorldEditor

The public `WorldEditor` directory currently exposes these root-level files/folders:

- `DataCtrl/`
- `Dialog/`
- `DockingBar/`
- `Scene/`
- `ToolBar/`
- `UI/`
- `res/`
- `MainFrm.cpp/.h`
- `StdAfx.cpp/.h`
- `Type.cpp/.h`
- `Util.cpp/.h`
- `ViewportManager.cpp/.h`
- `WorldEditor.cpp/.h`
- `WorldEditor.rc`
- `WorldEditor.vcxproj`
- `WorldEditor.vcxproj.filters`
- `WorldEditorDoc.cpp/.h`
- `WorldEditorView.cpp/.h`
- `resource.h`

`DataCtrl/` currently exposes these files in the public tree:

- `ActorInstanceAccessor.cpp/.h`
- `EffectAccessor.cpp/.h`
- `EffectData.h`
- `MapAccessorArea.cpp/.h`
- `MapAccessorOutdoor.cpp/.h`
- `MapAccessorTerrain.cpp/.h`
- `MapAccessorUndo.cpp`
- `MapManagerAccessor.cpp/.h`
- `MapManagerEnvironment.cpp`
- `MapManagerUndo.cpp`
- `MiniMapRenderHelper.cpp/.h`
- `ModelInstanceAccessor.cpp/.h`
- `NonPlayerCharacterInfo.cpp/.h`
- `ObjectAnimationAccessor.cpp/.h`
- `ObjectData.cpp/.h`
- `ObjectDataFile.cpp`
- `ObjectDataLight.cpp`
- `ShadowRenderHelper.cpp/.h`
- `UndoBuffer.cpp/.h`

The root README states the source baseline as Mainline, DirectX 9, Granny 2.11.8 and static DevIL 1.8.0. It describes adding `WorldEditor.vcxproj` to an existing ClientSource solution, targeting the correct TerrainLib/PRTerrainlib location, and running with a `D:\ymir work` data convention. It also documents a crash fix for selecting a `.spt` SpeedTree model on a brush.

## Architectural reading

The source layout strongly separates:

- application/frame/document/view bootstrap;
- data/control adapters (`DataCtrl`);
- scene-specific behavior;
- toolbar/docking resources;
- dialogs and UI controls;
- viewport management;
- undo/map manager services.

The rebuild should preserve these responsibilities while removing cyclic coupling and direct UI-to-engine mutation.
