#!/usr/bin/env python
# -*- coding: utf-8

# Copyright 2017-2019 The FIAAS Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta, MINYEAR
import os.path


"""Singleton configuration for k8s client"""

#: API server URL
api_server = "https://kubernetes.default.svc.cluster.local"
#: API token
api_token = ""
# Used by in_cluster_configuration. Takes precedence over `api_token` and `cert`.
api_token_source = None
#: API certificate
cert = None
#: Should the client verify the servers SSL certificates?
verify_ssl = True
#: Enable debugging
debug = False
#: Default timeout for most operations
timeout = 20
#: Default timeout for streaming operations, used while waiting for more events.
#: When reached, the library will usually info log and reconnect.
#: There's a few considerations when setting this value:
#: * On some servers, it might take this long to detect a dropped connection. This speaks for a low value,
#:   to detect the issue faster.
#: * When connecting, a resourceVersion is used to resume, if still valid. This speaks for a low value,
#:   to avoid them expiring.
#: * During idle periods, there might not be any new resourceVersions.
#:   Therefore a full quorum read each time a timeout is reached.
#:   This speaks for a high value.
#: 4.5 minutes is the default, set to detect the first case above in a reasonable time,
#:while being just below the default resourceVersion expiration of 5 minutes.
stream_timeout = 270
#: Default size of Watcher cache. If you expect a lot of events, you might want to increase this.
watcher_cache_size = 1000


# disables bandit warning for this line which triggers because the string contains 'token', which is fine
def use_in_cluster_config(token_file="/var/run/secrets/kubernetes.io/serviceaccount/token",  # nosec
                          ca_cert_file="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"):
    """
    Configure the client using the recommended configuration for accessing the API from within a Kubernetes cluster:
    https://kubernetes.io/docs/tasks/access-application-cluster/access-cluster/#accessing-the-api-from-a-pod
    """
    global api_token_source
    global verify_ssl
    api_token_source = FileTokenSource(token_file)
    if os.path.exists(ca_cert_file):
        verify_ssl = ca_cert_file


class FileTokenSource(object):
    """Read API token from token_file, exposing it via token(). Calls to token() will re-read the token from file if
    more than 1 minute has passed since the last read.

    Intended to support the BoundServiceAccountTokenVolume feature in Kubernetes 1.21 and later.
    """
    def __init__(self, token_file, now_func=datetime.now):
        self._token_file = token_file
        self._expires_at = datetime(MINYEAR, 1, 1)  # force read on initial call to _refresh_token
        self._refresh_interval = timedelta(minutes=1)
        self._token = self._refresh_token(now_func=now_func)  # fail on init if token_file can not be read

    def token(self, now_func=datetime.now):
        return self._refresh_token(now_func=now_func)

    def _refresh_token(self, now_func=datetime.now):
        now = now_func()
        if self._expires_at <= now:
            with open(self._token_file, 'r') as f:
                self._token = f.read().strip()
                self._expires_at = now + self._refresh_interval
        return self._token
