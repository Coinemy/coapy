# -*- coding: utf-8 -*-
# Copyright 2013, Peter A. Bigot
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at:
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
:copyright: Copyright 2013, Peter A. Bigot
:license: Apache-2.0
"""

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import logging
_log = logging.getLogger(__name__)

import re


class LinkValue(object):
    #: Regular expression to match strings enclosed in double quotes,
    #: allowing escaped double quotes inside.
    _DQUOTED_re = re.compile('"(?P<text>(?:[^"\\\\]|(?:\\\\.))*)"', re.DOTALL)

    #: Regular expression to match Link Format parameter value as
    #: unquoted token.
    _PTOKEN_re = re.compile('^[!#$%&\'()*+\-./0-9:<=>?@a-zA-Z\[\]^_`{|}~]{1,}$')

    @property
    def target_uri(self):
        """The URI-reference that is the target URI."""
        return self.__target_uri

    @property
    def params(self):
        """The map from parameter names to tokens."""
        return self.__params

    def __init__(self, target_uri, params):
        self.__target_uri = target_uri
        if not isinstance(params, dict):
            raise ValueError(params)
        self.__params = params

    def to_link_format(self):
        """Express link value as :rfc:`6690` link-value.

        The :attr:`target_uri` is wrapped in angle brackets.
        Parameters are converted to text ``key=value`` elements, where
        *value* is enclosed in double quotes if necessary.  All values
        are combined to a string using semicolon separators, and that
        string returned to the caller.

        Where *value* is ``None``, only ``key`` is included.

        Where *value* includes double quote characters (``"``), the
        quoted value escapes them with a single backslash for the
        purposes of parsing the resulting string: thus if ``k`` has
        value ``one"two``, the generated parameter will be
        ``k="one\\"two"``.  This done solely to avoid syntax errors on parsing;
        there is no corresponding conversion of ``\\"`` sequences to
        double-quote characters when the string representation is
        processed by :meth:`from_link_format`, and the semantics of
        escaped characters within a parameter value is the province of
        the specific parameter.

        No attempt is (currently) made to implement the requirements
        of :rfc:`2231`.
        """
        rv = []
        rv.append('<{}>'.format(self.__target_uri))
        if 0 < len(self.__params):
            # Sort for reproducibility
            for (k, v) in sorted(self.__params.iteritems()):
                if v is None:
                    rv.append(k)
                elif self._PTOKEN_re.match(v):
                    rv.append('{}={}'.format(k, v))
                else:
                    rv.append('{}="{}"'.format(k, v.replace(r'"', r'\"')))
        return ';'.join(rv)

    @classmethod
    def from_link_format(cls, text):
        link_values = []
        len_text = len(text)
        ofs = 0
        while (ofs < len_text) and ('<' == text[ofs]):
            rbi = text.find('>', ofs+1)
            if rbi < 0:
                raise Exception
            uri = text[ofs+1:rbi]
            ofs = rbi+1
            params = {}
            while (ofs < len_text) and (';' == text[ofs]):
                ofs += 1
                eqi = text.find('=', ofs)
                cmi = text.find(',', ofs)
                cli = text.find(';', ofs)
                ni = min([_i for _i in (eqi, cmi, cli, len_text) if (0 <= _i)])
                k = text[ofs:ni]
                ofs = ni
                if (ofs < len(text)) and ('=' == text[ofs]):
                    ofs += 1
                    mo = cls._DQUOTED_re.match(text, ofs)
                    if mo is not None:
                        v = mo.group('text')
                        ofs = mo.end()
                    else:
                        vei = min([_i for _i in (cmi, cli, len_text) if (0 <= _i)])
                        v = text[ofs:vei]
                        ofs = vei
                    params[k] = v
                else:
                    params[k] = None
            link_values.append(cls(uri, params))
            if (ofs < len_text) and (',' == text[ofs]):
                ofs += 1
            else:
                break
        if ofs < len_text:
            raise Exception
        return link_values
