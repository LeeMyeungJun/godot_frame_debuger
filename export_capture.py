import os, sys, json, traceback, bisect
import renderdoc as rd

cap = None
controller = None
status_path = os.environ['FRAMEDEBUGGER_STATUS']
try:
    rd.InitialiseReplay(rd.GlobalEnvironment(), [])
    cap = rd.OpenCaptureFile()
    result = cap.OpenFile(os.environ['FRAMEDEBUGGER_CAPTURE'], '', None)
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError('OpenFile failed: ' + str(result))
    if not cap.LocalReplaySupport():
        raise RuntimeError('Capture does not support local replay')
    result, controller = cap.OpenCapture(rd.ReplayOptions(), None)
    if result != rd.ResultCode.Succeeded:
        raise RuntimeError('OpenCapture failed: ' + str(result))

    textures = {int(t.resourceId): t for t in controller.GetTextures()}
    resources = {int(r.resourceId): r for r in controller.GetResources()}
    texture_dir = os.environ['FRAMEDEBUGGER_TEXTURES']
    os.makedirs(texture_dir, exist_ok=True)
    output_dir = os.path.dirname(os.environ['FRAMEDEBUGGER_OUTPUT'])
    os.makedirs(os.path.join(output_dir, 'frames'), exist_ok=True)
    saved = set()
    sampled_ids = set()
    draws = []
    write_events = {}
    write_usages = {getattr(rd.ResourceUsage, name) for name in (
        'ColorTarget', 'DepthStencilTarget', 'Clear', 'Discard', 'CPUWrite',
        'Copy', 'CopyDst', 'Resolve', 'ResolveDst', 'GenMips',
        'VS_RWResource', 'HS_RWResource', 'DS_RWResource', 'GS_RWResource',
        'PS_RWResource', 'CS_RWResource', 'All_RWResource',
        'MS_RWResource', 'TS_RWResource') if hasattr(rd.ResourceUsage, name)}

    def texture_info(rid):
        tex = textures[rid]
        resource = resources.get(rid)
        return {'id': str(rid), 'name': str(resource.name) if resource and resource.name else '',
                'width': int(tex.width), 'height': int(tex.height), 'format': tex.format.Name()}

    def save_texture(rid, relative, mip=0, slice_index=0, opaque=False):
        save = rd.TextureSave()
        save.resourceId = textures[rid].resourceId
        save.destType = rd.FileType.PNG
        save.alpha = rd.AlphaMapping.Discard if opaque else rd.AlphaMapping.Preserve
        save.mip = mip
        save.slice.sliceIndex = slice_index
        result = controller.SaveTexture(save, os.path.join(output_dir, relative))
        if result != rd.ResultCode.Succeeded:
            raise RuntimeError('SaveTexture failed for ' + relative + ': ' + str(result))
        return relative

    def sampled_image(rid, event_id):
        # Reuse only snapshots with the same last write, never future contents.
        if rid not in write_events:
            write_events[rid] = sorted({int(u.eventId) for u in controller.GetUsage(textures[rid].resourceId)
                                        if u.usage in write_usages})
        writes = write_events[rid]
        pos = bisect.bisect_right(writes, event_id)
        version = writes[pos - 1] if pos else 0
        key = (rid, version)
        path = 'textures/tex_{}_v{}.png'.format(rid, version)
        if key not in saved:
            save_texture(rid, path)
            saved.add(key)
        sampled_ids.add(rid)
        return path

    def walk(actions):
        for action in actions:
            if int(action.flags) & int(rd.ActionFlags.Drawcall):
                event_id = int(action.eventId)
                controller.SetFrameEvent(event_id, False)
                state = controller.GetPipelineState()
                targets = []
                for slot, target in enumerate(state.GetOutputTargets()):
                    rid = int(target.resource)
                    if rid not in textures:
                        continue
                    info = texture_info(rid)
                    info.update({'slot': slot, 'mip': int(target.firstMip), 'slice': int(target.firstSlice)})
                    targets.append(info)
                # Clears/copies between draws make the previous image unsuitable
                # for before/after comparison. Replay this exact draw's boundary.
                if targets:
                    controller.SetFrameEvent(max(0, event_id - 1), True)
                    for target in targets:
                        target['before'] = save_texture(int(target['id']),
                            'frames/event_{}_slot_{}_before.png'.format(event_id, target['slot']),
                            target['mip'], target['slice'], True)
                    controller.SetFrameEvent(event_id, True)
                    state = controller.GetPipelineState()
                    for target in targets:
                        target['image'] = save_texture(int(target['id']),
                            'frames/event_{}_slot_{}_after.png'.format(event_id, target['slot']),
                            target['mip'], target['slice'], True)
                bound = {}
                for binding in state.GetReadOnlyResources(rd.ShaderStage.Fragment, True):
                    rid = int(binding.descriptor.resource)
                    if rid == int(rd.ResourceId.Null()) or rid not in textures:
                        continue
                    tex = textures[rid]
                    resource = resources.get(rid)
                    raw_name = str(resource.name) if resource is not None and resource.name else ''
                    slot = int(getattr(binding.access, 'index', -1))
                    if rid not in bound:
                        bound[rid] = {
                            'id': str(rid), 'name': raw_name,
                            'width': int(tex.width), 'height': int(tex.height),
                            'format': tex.format.Name(), 'slots': [],
                            'image': sampled_image(rid, event_id)
                        }
                    if slot not in bound[rid]['slots']:
                        bound[rid]['slots'].append(slot)
                draws.append({
                    'event': event_id,
                    'name': str(action.GetName(controller.GetStructuredFile())),
                    'indices': int(getattr(action, 'numIndices', 0)),
                    'instances': int(getattr(action, 'numInstances', 1)),
                    'textures': list(bound.values()), 'targets': targets
                })
            walk(action.children)

    walk(controller.GetRootActions())
    api = str(controller.GetAPIProperties().pipelineType)
    result_data = {
        'capture': os.path.basename(os.environ['FRAMEDEBUGGER_CAPTURE']),
        'schema_version': 2,
        'api': api, 'draw_count': len(draws), 'texture_count': len(sampled_ids),
        'draws': draws
    }
    with open(os.environ['FRAMEDEBUGGER_OUTPUT'], 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, separators=(',', ':'))
    with open(status_path, 'w', encoding='utf-8') as f:
        f.write('ok')
except Exception:
    with open(status_path, 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
finally:
    if controller is not None:
        controller.Shutdown()
    if cap is not None:
        cap.Shutdown()
    try:
        rd.ShutdownReplay()
    except Exception:
        pass
sys.exit(0)
