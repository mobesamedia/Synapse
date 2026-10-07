"""Real Qt image decoding/encoding and portable bundle round trips, temporary data only."""
import importlib.util
import tempfile
from pathlib import Path
from PyQt6.QtGui import QImage, QColor
spec = importlib.util.spec_from_file_location('workspace_assets', Path(__file__).resolve().parents[1]/'workspace_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)
with tempfile.TemporaryDirectory(prefix='synapse-images-') as temp:
    root=Path(temp)
    source=root/'source.png'
    image=QImage(2400,1200,QImage.Format.Format_RGB32)
    image.fill(QColor('#3080aa'))
    assert image.save(str(source))
    first=assets.prepare_image(source,root/'profile-a')
    assert (first['width'],first['height'])==(1600,800)
    assert assets.prepare_image(source,root/'profile-a')==first
    assert len(list((root/'profile-a').iterdir()))==1
    document={'name':'Images','nodes':[{'id':1,'text':'Topic',**first,'imageWidth':first['width'],'imageHeight':first['height']}]}
    bundle=assets.export_bundle(document,root/'profile-a')
    imported=assets.import_bundle(bundle,root/'profile-b')
    assert imported==document
    assert (root/'profile-b'/first['image']).read_bytes()==(root/'profile-a'/first['image']).read_bytes()
    small=QImage(60,40,QImage.Format.Format_ARGB32)
    small.fill(QColor(255,0,0,80))
    assert small.save(str(source))
    second=assets.prepare_image(source,root/'profile-a')
    assert (second['width'],second['height'])==(60,40)
    assert second['image'].endswith('.png')
    for invalid in [dict(document,assets={}),dict(document,nodes=[{'image':'../../outside.png'}]),dict(bundle,assets={first['image']:'AAAA'}),dict(document,nodes=document['nodes']*41)]:
        try:assets.import_bundle(invalid,root/'unrelated-profile')
        except (ValueError,FileNotFoundError):pass
        else:raise AssertionError('invalid bundle accepted')
    try:assets.validate_document_images(dict(document,nodes=document['nodes']*20),root/'profile-a')
    except ValueError:pass
    else:raise AssertionError('pixel limit bypassed')
    import base64, hashlib, zlib
    svg=b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
    png=(root/'profile-a'/second['image']).read_bytes()
    animation=b'acTL'+(2).to_bytes(4,'big')+(0).to_bytes(4,'big')
    apng=png[:33]+(8).to_bytes(4,'big')+animation+(zlib.crc32(animation)&0xffffffff).to_bytes(4,'big')+png[33:]
    for raw in (svg,apng):
        key=hashlib.sha256(raw).hexdigest()+'.png'
        invalid={'nodes':[{'image':key}], 'assets':{key:base64.b64encode(raw).decode()}}
        try:assets.import_bundle(invalid,root/'profile-b')
        except ValueError:pass
        else:raise AssertionError('unsupported or animated data accepted')
    from unittest.mock import patch
    target=root/'durable.json'
    assets.atomic_write(target,b'old snapshot')
    with patch.object(assets.os,'replace',side_effect=OSError('synthetic failure')):
        try:assets.atomic_write(target,b'new snapshot')
        except OSError:pass
        else:raise AssertionError('failure simulation did not run')
    assert target.read_bytes()==b'old snapshot'
    print('PASS real Qt downscale, no upscaling, transparency, deduplication, portable export/import, missing/corrupt/path references, image count and pixel limits')
