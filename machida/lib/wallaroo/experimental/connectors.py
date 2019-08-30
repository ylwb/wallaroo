import hashlib
import logging
import math
from struct import unpack
import sys
import time


from . import (connector_wire_messages as cwm,
               AtLeastOnceSourceConnector,
               ProtocolError,
               ConnectorError)


if sys.version_info.major == 2:
    from .base_meta2 import BaseMeta, abstractmethod
else:
    from .base_meta3 import BaseMeta, abstractmethod


class BaseIter(BaseMeta):
    """
    A base class for creating iterator classes -- e.g. stateful iterators
    To use it, create your own subclass and implement the `__next__(self)`
    method.
    """
    def throw(self, type=None, value=None, traceback=None):
        raise StopIteration

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    @abstractmethod
    def __next__(self):
        raise NotImplementedError


class BaseSource(BaseMeta):
    """
    All sources should inherit BaseSource and implement four methods:
        - `__str__(self)`: a human readable description of the source
        - `reset(self, pos=0)`: a mechanism to reset the source to a point of
          reference `pos`. `pos` is a positive integer, and may be transformed
          further within the method body.
        - `point_of_ref(self)`: the current position of the source.
          e.g. for a file source, this could be the position at the end of
          reading a sequence of bytes.
        - `__next__(self)`: return a tuple of the next value and the new
          point of reference.
    """
    @abstractmethod
    def __str__(self):
        """
        Return a human readable description of the source
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self, pos=0):
        """
        Reset the source to position `pos`.
        `pos` is an integer point of reference. The source may do additional
        transformations in order to determine what internal position to reset
        to.
        """
        raise NotImplementedError

    @abstractmethod
    def point_of_ref(self):
        """
        Return the current point of reference
        """
        raise NotImplementedError

    @abstractmethod
    def __next__(self):
        """
        Return a tuple of the next message from the source and the point of
        reference after reading it.
        E.g. for a file source, it could be the bytes read, and the byte
        position after reading them.
        """
        raise NotImplementedError

    @abstractmethod
    def wallaroo_acked(self, point_of_ref):
        """
        When Wallaroo sends an ACK for our stream_id, this callback is
        called with the ack'ed point of reference.

        Implementing this callback is optional.
        """
        None

class FramedFileReader(BaseIter, BaseSource):
    """
    A framed file reader iterator with a resettable position.

    Usage: `FramedFileReader(filename)`.
    Data should have U32 length headers followed by data bytes, followed by
    the next datum's length header and bytes, and so on until the end of the
    file.
    """
    def __init__(self, filename):
        self.file = open(filename, mode='rb')
        self.name = filename.encode()
        self.key = filename.encode()

    def __str__(self):
        return ("FramedFileReader(filename: {}, closed: {}, point_of_ref: {})"
                .format(self.name, self.file.closed, self.point_of_ref()))

    def point_of_ref(self):
        try:
            return self.file.tell()
        except:
            return -1

    def reset(self, pos=0):
        logging.debug("resetting {} from {} to position {}"
            .format(self.__str__(), self.point_of_ref(), pos))
        self.file.seek(pos)

    def __next__(self):
        # read header
        h = self.file.read(4)
        if not h:
            raise StopIteration
        h_bytes = unpack('>I', h)[0]
        b = self.file.read(h_bytes)
        if not b:
            raise StopIteration
        return (b, self.file.tell())

    def close(self):
        self.file.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass

class LineFileReader(BaseIter, BaseSource):
    """
    An ASCII line-based file reader iterator with a resettable position.

    Usage: `LineFileReader(filename)`.
    """
    def __init__(self, filename):
        self.file = open(filename, mode='r')
        self.name = filename.encode()
        self.key = filename.encode()
        self.last_acked = None
        self.count = 0
        self.time_1st_iter = None
        self.iters_per_sec = None
        self.buf = None

    def __str__(self):
        return ("FramedFileReader(filename: {}, closed: {}, point_of_ref: {})"
                .format(self.name, self.file.closed, self.point_of_ref()))

    def point_of_ref(self):
        try:
            return self.file.tell()
        except:
            return -1

    def reset(self, pos=0):
        logging.debug("resetting {} from {} to position {}"
            .format(self.__str__(), self.point_of_ref(), pos))
        self.file.seek(pos)

    def __next__(self):
        count_boundary = 3
        self.count = self.count + 1
        if self.count == 1:
            self.time_1st_iter = time.time()
        # logging.debug("__next__ {}".format(self.count))

        if self.count < count_boundary:
            return (None, self.file.tell())
        if self.count == count_boundary:
            time_diff = time.time() - self.time_1st_iter
            num_iters = count_boundary - 1
            secs_per_iter = time_diff / num_iters
            self.iters_per_sec = math.trunc(1/secs_per_iter)
            logging.debug("iters_per_sec = {}".format(self.iters_per_sec))

        if self.last_acked != self.file.tell():
            return (None, self.file.tell())

        self.buf = self.file.readline()
        if not self.buf:
            raise StopIteration
        self.bytes_per_iter = math.trunc(len(self.buf) / self.iters_per_sec) + 1
        return (self.buf[0:self.bytes_per_iter], self.file.tell())

    def close(self):
        self.file.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass

    def wallaroo_acked(self, point_of_ref):
        self.last_acked = point_of_ref

class MultiSourceConnector(AtLeastOnceSourceConnector, BaseIter):
    """
    MultiSourceConnector

    Send data from mutliple sources in a round-robin fashion using the
    AtLeastOnceSourceConnector protocol and superclass.
    New sources may be added at any point.

    An iterator interface is used to read and send the next datum to the
    Wallaroo source, for use with an external loop, such as
    ```
    client = MultiSourceConnector(
        "0.0.1", "monster", "celsius at least once", "instance",
        args=None,
        required_params=['host', 'port', 'filenames'])

    # Open a connection with a hello message
    client.connect()

    params = client.params
    filenames = params.filenames.split(',')


    # Open FramedFileReader
    for fn in filenames:
        client.add_source(FramedFileReader(filename = fn))

    # Rely on the iterator method of our connector subclass
    client.join()
    print("Reached the end of all files. Shutting down.")
    ```
    """
    def __init__(self, version, cookie, program_name, instance_name, host,
                 port, delay=0):
        AtLeastOnceSourceConnector.__init__(self,
                                            version,
                                            cookie,
                                            program_name,
                                            instance_name,
                                            host,
                                            port,
                                            delay=delay)
        self.sources = {} # stream_id: [source instance, acked point of ref]
        self.closed_sources = {} # stream_id: acked point of ref
        self.keys = []
        self._idx = -1
        self.joining = set()
        self.open = set()
        self.pending_eos_ack = {}  # {stream_id: point_of_ref}
        self.closed = set()
        self._added_source = False

    def add_source(self, source):
        self._added_source = True
        # add to self.sources
        _id = self.get_id(source.name)
        # check if we already have source... if we do raise error
        if _id in self.sources:
            raise ConnectorError("Cannot add Source {}. A source exists"
                " with that ID: {}".format(source, self.sources[_id]))
        self.sources[_id] = [source, source.point_of_ref()]
        self.keys.append(_id)
        # add to joining set so we can control the starting sequence
        self.joining.add(_id)
        # send a notify
        self.notify(_id, source.name, source.point_of_ref())

    def remove_source(self, source):
        """
        Start an asynchronous closing of a source.
        This can only be completed via the `stream_closed` callback.
        """
        _id = self.get_id(source.name)
        if _id in self.sources:
            # Remove it from the open set
            if _id in self.open:
                self.open.remove(_id)
                # Add it to the set of sources pending closing
                point_of_ref = source.point_of_ref()
                self.pending_eos_ack[_id] = point_of_ref
                # send end of stream/EOS message
                self.end_of_stream(stream_id = _id) # aka EosMessage

    def _close_and_delete_source(self, source):
        key = self.get_id(source.name)
        if key in self.sources:
            try:
                del self.pending_eos_ack[key]
            except KeyError:
                raise ConnectorError("Cannot close source {}. It has not been"
                                     "properly removed yet. Please use "
                                     "`remove_source(source)` first."
                                     .format(source))
            # close and remove the source
            _, acked = self.sources.pop(key, (None, None))
            try:
                idx = self.keys.index(key) # value error
                self.keys.pop(idx) # index error
                if self._idx >= idx:
                    # to avoid skipping in the round-robin sender
                    self._idx -= 1
            except (ValueError, IndexError):
                # print warning
                logging.warning("Tried to delete source {} with key {} but "
                  "could not find it in keys collection: {}"
                  .format(source, key, self.keys))
            source.close()
            # add it to closed so we keep track of it
            self.closed.add(key)
            self.closed_sources[key] = acked

    @staticmethod
    def get_id(bs):
        """
        Repeatable hash from bytes to 64-bit unsigned integer using a truncated
        SHA256.
        """
        h = hashlib.new('sha256')
        h.update(bs)
        return int(h.hexdigest()[:16], 16)

    # Make this class an iterable:
    def __next__(self):
        if len(self.keys) > 0:
            # get next position
            self._idx = (self._idx + 1) % len(self.keys)
            # get key of that position
            key = self.keys[self._idx]
            # if stream is not in an open state, return nothing.
            if not key in self.open:
                return None
            try:
                # get source at key
                source = self.sources[key][0]
                # get value from source
                value, point_of_ref = next(source)
                if value is None:
                    return None
                # send it as a message
                msg = cwm.Message(
                    stream_id = key,
                    message_id = point_of_ref,
                    event_time = 0,
                    key = source.key,
                    message = value)
                return msg
            except StopIteration:
                # if the source threw a StopIteration, remove it
                source, _ = self.sources.get(key, (None, None))
                if source:
                    self.remove_source(source)
                return None
            except IndexError:
                # Index might have overflowed due to manual remove_source
                # will be corrected in the next iteration
                return None
        elif not self._added_source:
            # In very fast select loops, we might reach the end condition
            # before we have a chance to add our first source, so keep
            # spinning
            return None
        elif not self.closed:
            # There's a race when added_source can be set, but keys isn't
            # populated yet. If closed is empty, we haven't yet closed any
            # sources, so shouldn't terminate the loop
            return None
        else:
            logging.debug("__next__: raising StopIteration")
            logging.debug("keys: {}, joining: {}, open: {}, pending_eos_ack: {}, closed: {}, _added_source: {}".format(self.keys, self.joining, self.open, self.pending_eos_ack, self.closed, self._added_source))
            raise StopIteration

    def stream_added(self, stream):
        logging.debug("MultiSourceConnector added {}".format(stream))
        source, acked = self.sources.get(stream.id, (None, None))
        if source:
            if stream.point_of_ref != source.point_of_ref():
                source.reset(stream.point_of_ref)

        # probably got this as part of the _handle_ok logic. Store the ack
        # and use when a source matching the stream id is added
        else:
            self.sources[stream.id] = [None, stream.point_of_ref]

    def stream_removed(self, stream):
        logging.debug("MultiSourceConnector removed {}".format(stream))
        pass

    def stream_opened(self, stream):
        logging.debug("MultiSourceConnector stream_opened {}".format(stream))
        source, acked = self.sources.get(stream.id, (None, None))
        if source:
            if stream.id in self.joining:
                self.joining.remove(stream.id)
                if stream.point_of_ref != source.point_of_ref():
                    source.reset(stream.point_of_ref)
            self.open.add(stream.id)
        else:
            raise ConnectorError("Stream {} was opened for unknown source. "
                                 "Please use the add_source interface."
                                 .format(stream))

    def stream_closed(self, stream):
        logging.debug("MultiSourceConnector closed {}".format(stream))
        source, acked = self.sources.get(stream.id, (None, None))
        if source:
            if stream.id in self.open:
                # source was open so move it back to joining state
                self.open.remove(stream.id)
                self.joining.add(stream.id)
            elif stream.id in self.pending_eos_ack:
                # source was pending eos ack, but that was interrupted
                # move it back to joining
                del self.pending_eos_ack[stream.id]
                self.joining.add(stream.id)
            elif stream.id in self.closed:
                logging.debug("tried to close an already closed source: {}"
                  .format(Source))
            else:
                pass
        else:
            pass

    def stream_acked(self, stream):
        logging.debug("MultiSourceConnector acked {}".format(stream))
        source, acked = self.sources.get(stream.id, (None, None))
        source.wallaroo_acked(stream.point_of_ref)
        if source:
            # check if there's an eos pending this ack
            eos_point_of_ref = self.pending_eos_ack.get(stream.id, None)
            if eos_point_of_ref:
                logging.debug("Stream {} got awaited EOS Ack for {}"
                              .format(stream, eos_point_of_ref))
                # source was pending eos ack
                # check ack's point of ref
                if stream.point_of_ref == eos_point_of_ref:
                    # can finish closing it now
                    self._close_and_delete_source(source)
                    return
                elif stream.point_of_ref < eos_point_of_ref:
                    pass
                else:
                    raise ConnectorError("Got ack point of ref that is larger"
                        " than the ended stream's point of ref.\n"
                        "Expected: {}, Received: {}"
                        .format(eos_point_of_ref, stream))
            elif isinstance(acked, int):  # acked may be 0 & use this clause!
                # regular ack (incremental ack of a live stream)
                if stream.point_of_ref < acked:
                    logging.warning("got an ack for older point of reference"
                        " for stream {}".format(stream))
                    source.reset(stream.point_of_ref)
            else:
                # source was added before connect()\handle_ok => reset
                source.reset(stream.point_of_ref)

            # update acked point of ref for the source
            self.sources[stream.id][1] = stream.point_of_ref

        elif stream.id in self.closed:
            pass
        else:
            raise ConnectorError("Stream {} was opened for unknown source. "
                                 "Please use the add_source interface."
                                 .format(stream))

