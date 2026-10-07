"""Bounded, content-addressed images in the Anki profile, outside add-on updates."""
import base64
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

MAX_SOURCE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_BYTES = 1024 * 1024
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_IMAGES = 40
MAX_DOCUMENT_PIXELS = 24_000_000
IMAGE_ID = re.compile(r'^[a-f0-9]{64}\.(?:png|jpg)$')


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def image_refs(document):
    entries = document.get('objects', document.get('nodes', []))
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError('Invalid document objects.')
    refs = [item['image'] for item in entries if item.get('image')]
    if len(refs) > MAX_IMAGES or any(not isinstance(ref, str) or not IMAGE_ID.fullmatch(ref) for ref in refs):
        raise ValueError('Invalid image references or too many images (maximum 40).')
    return set(refs)


def inspect_image(raw, max_pixels=1600*1600):
    from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
    from PyQt6.QtGui import QImageReader
    buffer = QBuffer()
    buffer.setData(QByteArray(raw))
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    reader = QImageReader(buffer)
    size = reader.size()
    if max_pixels == 1600*1600:
        if bytes(reader.format()).lower() not in (b'png', b'jpg', b'jpeg'):
            raise ValueError('Stored images must be PNG or JPEG.')
        # APNG animation can decode many frames despite small file dimensions.
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):
            offset = 8
            while offset+12 <= len(raw):
                length = int.from_bytes(raw[offset:offset+4], 'big')
                if raw[offset+4:offset+8] == b'acTL':
                    raise ValueError('Animated image bundles are not supported.')
                offset += length+12
    if size.width() < 1 or size.height() < 1 or size.width()*size.height() > max_pixels or (max_pixels==1600*1600 and max(size.width(),size.height())>1600):
        raise ValueError('Image dimensions exceed the limit.')
    return reader, buffer, size


def prepare_image(path, folder):
    from PyQt6.QtCore import QByteArray, QBuffer, QIODevice, QSize, Qt
    from PyQt6.QtGui import QImageWriter
    source = Path(path)
    if source.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('Image is larger than 20 MB.')
    raw = source.read_bytes()
    reader, buffer, size = inspect_image(raw, 24_000_000)
    if bytes(reader.format()).lower() not in (b'png', b'jpeg', b'jpg', b'webp'):
        raise ValueError('Use PNG, JPEG or WebP images.')
    reader.setAutoTransform(True)
    reader.setScaledSize(size.scaled(QSize(min(1600, max(size.width(),size.height())), min(1600, max(size.width(),size.height()))), Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        raise ValueError('Could not decode image.')
    ext = 'png' if image.hasAlphaChannel() else 'jpg'
    for edge in (1600, 1200, 900, 640):
        edge = min(edge, max(image.width(), image.height()))
        resized = image.scaled(edge, edge, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        output = QByteArray()
        target = QBuffer(output)
        target.open(QIODevice.OpenModeFlag.WriteOnly)
        writer = QImageWriter(target, ext.encode())
        writer.setQuality(82)
        if not writer.write(resized):
            raise ValueError('Could not encode image.')
        encoded = bytes(output)
        if len(encoded) <= MAX_IMAGE_BYTES:
            key = hashlib.sha256(encoded).hexdigest()+'.'+ext
            dest = Path(folder)/key
            if not dest.exists():
                atomic_write(dest, encoded)
            return {'image': key, 'width': resized.width(), 'height': resized.height()}
    raise ValueError('Image cannot be reduced to the size limit.')


def validate_document_images(document, folder, pending=None):
    pending = pending or {}
    pixels = {}
    dimensions = {}
    for key in image_refs(document):
        raw = pending.get(key)
        if raw is None:
            path = Path(folder)/key
            if path.stat().st_size > MAX_IMAGE_BYTES:
                raise ValueError('Image exceeds size limit.')
            raw = path.read_bytes()
        reader, buffer, size = inspect_image(raw)
        if reader.read().isNull():
            raise ValueError('Invalid image data.')
        pixels[key] = size.width()*size.height()
        dimensions[key] = (size.width(),size.height())
    entries = document.get('objects', document.get('nodes', []))
    if sum(pixels.get(o.get('image'), 0) for o in entries) > MAX_DOCUMENT_PIXELS:
        raise ValueError('Images exceed the document limit (24 megapixels).')
    return dimensions


def export_bundle(document, folder):
    validate_document_images(document, folder)
    result = dict(document)
    result['assets'] = {key: base64.b64encode((Path(folder)/key).read_bytes()).decode('ascii') for key in image_refs(document)}
    return result


def import_bundle(document, folder):
    """Validate everything before installing any referenced image. Ignore unused assets."""
    pending = {}
    supplied = document.get('assets', {})
    if not isinstance(supplied, dict):
        raise ValueError('Invalid image bundle.')
    for key in image_refs(document):
        if key not in supplied:
            if not (Path(folder)/key).is_file():
                raise ValueError('An image is missing from the import.')
            continue
        value = supplied[key]
        if not isinstance(value, str) or len(value) > (MAX_IMAGE_BYTES+2)//3*4:
            raise ValueError('Image exceeds size limit.')
        raw = base64.b64decode(value, validate=True)
        if len(raw)>MAX_IMAGE_BYTES or hashlib.sha256(raw).hexdigest()!=key.split('.')[0]:
            raise ValueError('Invalid image checksum.')
        pending[key] = raw
    dimensions = validate_document_images(document, folder, pending)
    for entry in document.get('objects',document.get('nodes',[])):
        if entry.get('image'):
            entry['imageWidth'],entry['imageHeight'] = dimensions[entry['image']]
    for key, raw in pending.items():
        path = Path(folder)/key
        if not path.exists():
            atomic_write(path, raw)
    return {key: value for key, value in document.items() if key != 'assets'}
