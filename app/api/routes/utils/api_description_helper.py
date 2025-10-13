#  Copyright 2023 ExxonMobil Technology and Engineering Company
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from app.resources.required_roles import RecordRequiredRoles


class APIDescriptionHelper(object):
    """The class can help with building API routes description."""

    description_template_roles = "<br><br>\
        Required roles: {required_roles}.<br> \
        In addition, users must be members of a data group(ACL) to access the data."  # noqa: N400

    @classmethod
    def append_manage_roles(cls, description: str, anyof: bool = True) -> str:
        """Append manage roles to description.

        :param description: description
        :type description: str
        :param anyof: anyof, defaults to True
        :type anyof: bool
        :return: description with manage roles
        :rtype: str
        """
        return cls._join(
            description,
            RecordRequiredRoles.RECORD_MANAGE_ROLES,
            anyof,
        )

    @classmethod
    def append_read_roles(cls, description: str, anyof: bool = True) -> str:
        """Append read roles to description.

        :param description: description
        :type description: str
        :param anyof: anyof, defaults to True
        :type anyof: bool
        :return: description with read roles
        :rtype: str
        """
        return cls._join(
            description,
            RecordRequiredRoles.RECORD_READ_ROLES,
            anyof,
        )

    @classmethod
    def append_joined_roles(cls, description: str, anyof: bool = True) -> str:
        """Append joined roles to description.

        :param description: description
        :type description: str
        :param anyof: anyof, defaults to True
        :type anyof: bool
        :return: description with joined roles
        :rtype: str
        """
        return cls._join(
            description,
            RecordRequiredRoles.RECORD_READ_ROLES + RecordRequiredRoles.RECORD_MANAGE_ROLES,
            anyof,
        )

    @classmethod
    def _join(cls, description: str, roles: list, anyof: bool) -> str:
        """Update description with roles.

        :param description: description
        :type description: str
        :param roles: roles
        :type roles: list
        :param anyof: anyof
        :type anyof: bool
        :return: description with roles
        :rtype: str
        """
        roles_txt = cls.description_template_roles.format(
            required_roles=cls._join_roles(roles, anyof),
        )

        return f"{description}{roles_txt}"

    @staticmethod
    def _join_roles(roles: list, anyof: bool) -> str:
        """Prepare roles string with logic delimiter.

        Example: role1 and role2; role1 or role2

        :param roles: roles
        :type roles: list
        :param anyof: any or all
        :type anyof: bool
        :return: prepared roles
        :rtype: str
        """
        delim = " or " if anyof else " and "
        return delim.join([f"`{role}`" for role in roles])
