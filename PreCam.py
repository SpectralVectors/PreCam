bl_info = {
    "name": "PreCam",
    "author": "Kolupsy, iceythe (Kaio), Spectral Vectors",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "Click on Camera or F3 > PreCam",
    "description": "A preview of the camera view overlayed on the 3D Viewport",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy, gpu, numpy as np
from gpu_extras.presets import draw_texture_2d
from bpy.app.handlers import persistent


class LiveCapture_OT_capture(bpy.types.Operator):
    bl_idname = 'livecapture.capture'
    bl_label = 'Live Capture'


    def execute(self, context):
        self.report({'WARNING'}, 'Operator has no execution. Use as modal.')
        return {'CANCELLED'}


    def invoke(self, context, event):
        scene = context.scene
        render = scene.render

        resolution_x = render.resolution_x
        resolution_y = render.resolution_y
        downscale_factor = 4

        horizontal_resolution = int(resolution_x/downscale_factor)
        vertical_resolution = int(resolution_y/downscale_factor)

        offscreen = gpu.types.GPUOffScreen(horizontal_resolution, vertical_resolution)

        if not 'LiveTexture' in bpy.data.images.keys():
            bpy.data.images.new(
                'LiveTexture',
                horizontal_resolution,
                vertical_resolution,
                alpha=True)

        LiveTexture = bpy.data.images['LiveTexture']
        LiveTexture.pack()
        LiveTexture.use_fake_user = True
        LiveTexture.colorspace_settings.name = 'Linear'


        def draw(
            context=context, 
            scene=scene, 
            horizontal_resolution=horizontal_resolution, 
            vertical_resolution=vertical_resolution, 
            offscreen=offscreen, 
            LiveTexture=LiveTexture):

            view_layer = context.view_layer
            space_data = context.space_data
            region = context.region

            object = context.object
            Camera = object if object.type == 'CAMERA' else bpy.data.objects['Camera']

            view_matrix = Camera.matrix_world.inverted()
            projection_matrix = Camera.calc_matrix_camera(
                context.evaluated_depsgraph_get(),
                x=horizontal_resolution,
                y=vertical_resolution)

            original_overlays = context.space_data.overlay.show_overlays
            context.space_data.overlay.show_overlays = False
            offscreen.draw_view3d(
                scene,
                view_layer,
                space_data,
                region,
                view_matrix,
                projection_matrix)
            context.space_data.overlay.show_overlays = original_overlays

            gpu.state.depth_mask_set(False)
            buffer = np.array(
                offscreen.texture_color.read(),
                dtype='float32').flatten(order='F')
            buffer = np.divide(buffer, 255)
            LiveTexture.pixels.foreach_set(buffer)

            area_width = context.area.width
            preview_width = area_width/6
            horizontal_size = int(preview_width*(resolution_x/resolution_y))
            vertical_size = int(preview_width)
            offset = 20
            horizontal_location = int(area_width - horizontal_size - offset)

            draw_texture_2d(
                offscreen.texture_color,
                (horizontal_location, offset),
                horizontal_size,
                vertical_size)
        
        self.report({'INFO'}, 'Start realtime update.')
        self._handler = bpy.types.SpaceView3D.draw_handler_add(
            draw, (), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


    def modal(self, context, event):
        if event.type == 'ESC':
            return self.finish(context)
        return {'PASS_THROUGH'}


    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        self.report({'INFO'}, 'Stopped realtime update.')
        return {'FINISHED'}


@persistent
def on_active_object_changed():
    active = bpy.context.view_layer.objects.active
    if active.type == 'CAMERA':
        print('It is a Camera')
        bpy.ops.livecapture.capture('INVOKE_DEFAULT')
    else:
        print('NOT A CAMERA!!!')


def custom_draw(self, context):
    self.layout.operator(operator="livecapture.capture",text="PreCam", icon='SCENE')


def menu_func(self, context):
    self.layout.operator(LiveCapture_OT_capture.bl_idname)

cam_check = object()


def register(cam_check=cam_check):
    bpy.utils.register_class(LiveCapture_OT_capture)

    bpy.types.VIEW3D_MT_object.append(menu_func)
    bpy.types.VIEW3D_MT_view.append(custom_draw)
    bpy.app.handlers.load_post.append(on_active_object_changed)

    # Subscribe to active object changes.
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=cam_check,
        args=(),
        notify=on_active_object_changed)


def unregister(cam_check=cam_check):
    bpy.msgbus.clear_by_owner(cam_check)
    bpy.app.handlers.load_post.remove(on_active_object_changed)
    bpy.types.VIEW3D_MT_view.remove(custom_draw)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

    bpy.utils.unregister_class(LiveCapture_OT_capture)


if __name__ == "__main__":
    register()
