#!/usr/bin/env python

if __name__ == "__main__":
    from sugar.activity import bundlebuilder
    from sugar.bundle.activitybundle import ActivityBundle
    b = ActivityBundle('.')
    __, name = b.get_bundle_id().rsplit('.',1)
    bundlebuilder.start(name)
