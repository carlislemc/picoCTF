"""
Setup for the API
"""

import api

log = api.logger.use(__name__)

def index_mongo():
    """
    Ensure the mongo collections are indexed.
    """

    db = api.common.get_conn()

    log.debug("Ensuring mongo is indexed.")

    if "uid" not in db.users.index_information():
       db.users.create_index("uid", unique=True, name="unique uid")
    if "username" not in db.users.index_information():
       db.users.create_index("username", unique=True, name="unique username")
    if "tid" not in db.users.index_information():
       db.users.create_index("tid")

    if "gid" not in db.groups.index_information():
       db.groups.create_index("gid", unique=True, name="unique gid")

    if "pid" not in db.groups.index_information():
       db.problems.create_index("pid", unique=True, name="unique pid")

    try:
       db.submissions.create_index([("tid", 1), ("uid", 1), ("correct", 1)])
       db.submissions.create_index([("uid", 1), ("correct", 1)])
       db.submissions.create_index([("tid", 1), ("correct", 1)])
       db.submissions.create_index([("pid", 1), ("correct", 1)])
    except:
       pass
    if "uid" not in db.submissions.index_information():
       db.submissions.create_index("uid")
    if "tid" not in db.submissions.index_information():
       db.submissions.create_index("tid")

    if "team_names" not in db.teams.index_information():
       db.teams.create_index("team_name", unique=True, name="unique team names")
    if "country" not in db.teams.index_information():
       db.teams.create_index("country")

    if "name" not in db.shell_servers.index_information():
       db.shell_servers.create_index("name", unique=True, name="unique shell name")
    if "sid" not in db.shell_servers.index_information():
       db.shell_servers.create_index("sid", unique=True, name="unique shell sid")

    if "expireAt" not in db.cache.index_information():
       db.cache.create_index("expireAt", expireAfterSeconds=0)
    if "kwargs" not in db.cache.index_information():
       db.cache.create_index("kwargs", name="kwargs")
    try:
       db.cache.create_index([("function", 1), ("ordered_kwargs", 1)])
    except:
       pass
    if "args" not in db.cache.index_information():
       db.cache.create_index("args", name="args")
