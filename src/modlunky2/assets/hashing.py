import hashlib

def md5sum_path(path, chunk_size=8192):
    """ Streaming md5 digest from a path."""

    with path.open("rb") as file_:
        md5sum = hashlib.md5()
        chunk = file_.read(chunk_size)
        while chunk:
            md5sum.update(chunk)
            chunk = file_.read(chunk_size)
        return md5sum.hexdigest().encode()
