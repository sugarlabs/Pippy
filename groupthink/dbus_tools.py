import dbus

inttypes = (dbus.Int16, dbus.Int32, dbus.Int64, 
                  dbus.Byte, dbus.UInt16, dbus.UInt32, dbus.UInt64)
booltypes = (dbus.Boolean)
floattypes = (dbus.Double)
strtypes = (dbus.ByteArray, dbus.String, dbus.UTF8String, dbus.Signature,
                   dbus.ObjectPath)

def undbox(x):
    if isinstance(x, inttypes):
        return int(x)
    elif isinstance(x, booltypes):
        return bool(x)
    elif isinstance(x, strtypes):
        return str(x)
    elif isinstance(x, floattypes):
        return float(x)
    elif isinstance(x, (dbus.Struct, tuple)):
        return tuple(undbox(y) for y in x)
    elif isinstance(x, (dbus.Array, list)):
        return [undbox(y) for y in x]
    elif isinstance(x, (dbus.Dictionary, dict)):
        return dict((undbox(a),undbox(b)) for (a,b) in x.iteritems())
    else:
        return x
