# -*- coding: utf-8 -*-
"""
`resolver` -- Resolve Identifiers to Image Paths
================================================
"""
from logging import getLogger
import loris_exception
from os.path import join, exists, isfile
from urllib import unquote
from shutil import copy
from os import makedirs
from os.path import dirname
from loris_exception import ResolverException
from urllib import urlretrieve

logger = getLogger(__name__)

class _AbstractResolver(object):
    def __init__(self, config):
        self.config = config

    def is_resolvable(self, ident):
        """
        The idea here is that in some scenarios it may be cheaper to check 
        that an id is resolvable than to actually resolve it. For example, for 
        an HTTP resolver, this could be a HEAD instead of a GET.

        Args:
            ident (str):
                The identifier for the image.
        Returns:
            bool
        """
        e = self.__class__.__name__
        raise NotImplementedError('is_resolvable() not implemented for %s' % (cn,))

    def resolve(self, ident):
        """
        Given the identifier of an image, get the path (fp) and format (one of. 
        'jpg', 'tif', or 'jp2'). This will likely need to be reimplemented for
        environments and can be as smart or dumb as you want.
        
        Args:
            ident (str):
                The identifier for the image.
        Returns:
            (str, str): (fp, format)
        Raises:
            ResolverException when something goes wrong...
        """
        e = self.__class__.__name__
        raise NotImplementedError('resolve() not implemented for %s' % (cn,))


class SimpleFSResolver(_AbstractResolver):

    def __init__(self, config):
        super(SimpleFSResolver, self).__init__(config)
        self.cache_root = self.config['src_img_root']

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        return exists(fp)

    @staticmethod
    def _format_from_ident(ident):
        return ident.split('.')[-1]

    def resolve(self, ident):
        # For this dumb version a constant path is prepended to the identfier 
        # supplied to get the path It assumes this 'identifier' ends with a file 
        # extension from which the format is then derived.
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        logger.debug('src image: %s' % (fp,))

        if not exists(fp):
            public_message = 'Source image not found for identifier: %s.' % (ident,)
            log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
            logger.warn(log_message)
            raise ResolverException(404, public_message)

        format = SimpleFSResolver._format_from_ident(ident)
        logger.debug('src format %s' % (format,))

        return (fp, format)

class WebBPLResolver(_AbstractResolver):
    '''
    Example resolver that one might use if image files were coming from
    mounted network storage. The first call to `resolve()` copies the source
    image into a local cache; subsequent calls use local copy from the cache.

    The config dictionary MUST contain
     * `cache_root`, which is the absolute path to the directory where images
        should be cached.
     * `source_root`, the root directory for source images.
    '''
    def __init__(self, config):
        super(WebBPLResolver, self).__init__(config)
        self.cache_root = self.config['cache_root']
        self.source_root = self.config['source_root']

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        return exists(fp)

    @staticmethod
    def _format_from_ident(ident):
        if ident.find('.') == -1:
            return 'jp2'
        else:
            return ident.split('.')[-1]

    def resolve(self, ident):
        ident = unquote(ident)
        local_fp = join(self.cache_root, ident)
        print ident
        print local_fp

        if exists(local_fp):
            print "I should not be here"
            format = WebBPLResolver._format_from_ident(ident)
            logger.debug('src image from local disk: %s' % (local_fp,))
            return (local_fp, format)
        else:
            print "I should be here"
            #fp = join(self.source_root, ident)
            fp = self.source_root + ident + '/datastreams/accessMaster/content'
            logger.debug('src image: %s' % (fp,))

            #FIXME: Should check header. Sadly, import requests then the following gives 401?
            #r = requests.head("http://fedoradev.bpl.org/fedora/objects/bpl-dev:k930cv929/datastreams/thumbnail300/content")
            #print r.status_code
            #if not exists(fp):
                #public_message = 'Source image not found for identifier: %s.' % (ident,)
                #log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
                #logger.warn(log_message)
                #raise ResolverException(404, public_message)

            #This always errors?
            try:
                makedirs(dirname(local_fp))
            except:
                logger.debug("makedirs still does nothing")

            #jp2 = urllib2.urlopen(urllib2.Request(fp))
            urlretrieve(fp, local_fp)

            #copy(fp, local_fp)
            logger.info("Copied %s to %s" % (fp, local_fp))

            format = WebBPLResolver._format_from_ident(ident)
            logger.debug('src format %s' % (format,))

            return (local_fp, format)

class SourceImageCachingResolver(_AbstractResolver):
    '''
    Example resolver that one might use if image files were coming from
    mounted network storage. The first call to `resolve()` copies the source
    image into a local cache; subsequent calls use local copy from the cache.
 
    The config dictionary MUST contain 
     * `cache_root`, which is the absolute path to the directory where images 
        should be cached.
     * `source_root`, the root directory for source images.
    '''
    def __init__(self, config):
        super(SourceImageCachingResolver, self).__init__(config)
        self.cache_root = self.config['cache_root']
        self.source_root = self.config['source_root']

    def is_resolvable(self, ident):
        ident = unquote(ident)
        fp = join(self.cache_root, ident)
        return exists(fp)

    @staticmethod
    def _format_from_ident(ident):
        return ident.split('.')[-1]

    def resolve(self, ident):
        ident = unquote(ident)
        local_fp = join(self.cache_root, ident)

        if exists(local_fp):
            format = SourceImageCachingResolver._format_from_ident(ident)
            logger.debug('src image from local disk: %s' % (local_fp,))
            return (local_fp, format)
        else:
            fp = join(self.source_root, ident)
            logger.debug('src image: %s' % (fp,))
            if not exists(fp):
                public_message = 'Source image not found for identifier: %s.' % (ident,)
                log_message = 'Source image not found at %s for identifier: %s.' % (fp,ident)
                logger.warn(log_message)
                raise ResolverException(404, public_message)

            makedirs(dirname(local_fp))
            copy(fp, local_fp)
            logger.info("Copied %s to %s" % (fp, local_fp))

            format = SourceImageCachingResolver._format_from_ident(ident)
            logger.debug('src format %s' % (format,))

            return (local_fp, format)




