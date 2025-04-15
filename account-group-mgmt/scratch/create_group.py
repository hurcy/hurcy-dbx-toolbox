import yaml
import logging
import argparse
from databricks.sdk import AccountClient
from databricks.sdk.service import iam
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UserGroupManager:
    def __init__(self, client):
        self.client = client
        self.existing_groups = self._load_existing_groups()
        self.group_parent_map = self._build_parent_mapping()

    def _create_user(self, name, email):
        """Create user and return ID."""
        try:
            # Check existing users
            for user in self.client.users.list():
                if user.user_name == email:
                    logger.info(f"Existing user found: {name} ({email})")
                    return user.id

            # Create new user
            user = self.client.users.create(display_name=name, user_name=email)
            logger.info(f"User created: {name} ({email})")
            return user.id
        except Exception as e:
            logger.error(f"Error creating/finding user: {e}")
            raise

    def _create_group(self, name):
        """Create group and return ID."""
        try:
            # Check existing groups
            for group in self.client.groups.list():
                if group.display_name == name:
                    logger.info(f"Existing group found: {name}")
                    return group.id

            # Create new group
            group = self.client.groups.create(display_name=name)
            logger.info(f"Group created: {name}")
            return group.id
        except Exception as e:
            logger.error(f"Error creating/finding group: {e}")
            raise

    def _add_members_to_group(self, group_id, member_ids):
        """Add members to group."""
        if not member_ids:
            return  # No action if no members

        try:
            # Prepare member values
            member_values = [{"value": member_id} for member_id in member_ids]

            # Add members using patch function
            self.client.groups.patch(
                id=group_id,
                schemas=[
                    iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP
                ],
                operations=[
                    iam.Patch(
                        op=iam.PatchOp.ADD,
                        value={"members": member_values},
                    )
                ],
            )
            logger.info(
                f"Members added to group: {len(member_ids)} members -> Group ID {group_id}"
            )
        except Exception as e:
            logger.error(f"Error adding members to group: {e}")
            raise

    def _load_existing_groups(self):
        return {g.display_name: g for g in self.client.groups.list()}

    def _build_parent_mapping(self):
        parent_map = defaultdict(list)
        for group in self.existing_groups.values():
            members = self.client.groups.get(id=group.id).members
            if members:
                for member in members:
                    if member.type == "group":
                        parent_map[member.value].append(group.id)
        return parent_map

    def validate_structure(self, yaml_groups):
        """Validate current structure against YAML definition"""
        report = {"missing_groups": [], "extra_groups": [], "mismatched_parents": []}

        # Check for missing groups
        yaml_group_names = self._get_all_group_names(yaml_groups)
        existing_group_names = set(self.existing_groups.keys())
        report["missing_groups"] = list(yaml_group_names - existing_group_names)
        report["extra_groups"] = list(existing_group_names - yaml_group_names)

        # Check parent relationships
        self._check_parent_relationships(yaml_groups, report)

        return report

    def _get_all_group_names(self, groups):
        names = set()
        for group in groups:
            names.add(group["name"])
            if "groups" in group:
                names.update(self._get_all_group_names(group["groups"]))
        return names

    def _check_parent_relationships(self, yaml_groups, report, parent_id=None):
        for group in yaml_groups:
            group_name = group["name"]
            if group_name not in self.existing_groups:
                continue

            current_parents = self.group_parent_map.get(
                self.existing_groups[group_name].id, []
            )
            if parent_id and parent_id not in current_parents:
                report["mismatched_parents"].append(
                    {
                        "group": group_name,
                        "expected_parent": parent_id,
                        "current_parents": current_parents,
                    }
                )

            if "groups" in group:
                self._check_parent_relationships(
                    group["groups"], report, self.existing_groups[group_name].id
                )

    def sync_structure(self, yaml_groups):
        """Synchronize Databricks groups with YAML structure"""
        # Step 1: Delete extra groups
        # self._delete_extra_groups(yaml_groups)

        # Step 2: Create missing groups
        self._create_missing_groups(yaml_groups)

        # Step 3: Rebuild parent relationships
        self._sync_parent_relationships(yaml_groups)

        # Step 4: Sync users
        self._sync_users(yaml_groups)

    def _delete_extra_groups(self, yaml_groups):
        existing_names = set(self.existing_groups.keys())
        yaml_names = self._get_all_group_names(yaml_groups)
        for group_name in existing_names - yaml_names:
            logger.info(f"Deleting obsolete group: {group_name}")
            self.client.groups.delete(id=self.existing_groups[group_name].id)

    def _create_missing_groups(self, groups, parent_id=None):
        for group in groups:
            group_name = group["name"]
            if group_name not in self.existing_groups:
                new_group = self.client.groups.create(display_name=group_name)
                self.existing_groups[group_name] = new_group
                logger.info(f"Created new group: {group_name}")

            if parent_id:
                self._ensure_parent_relationship(group_name, parent_id)

            if "groups" in group:
                self._create_missing_groups(
                    group["groups"], self.existing_groups[group_name].id
                )

    def _sync_parent_relationships(self, groups, parent_id=None):
        for group in groups:
            group_name = group["name"]
            current_group = self.existing_groups[group_name]

            # Remove incorrect parents
            current_parents = self.group_parent_map.get(current_group.id, [])
            for cp in current_parents:
                if not parent_id or cp != parent_id:
                    self._remove_from_parent(current_group.id, cp)

            # Add correct parent
            if parent_id:
                self._ensure_parent_relationship(group_name, parent_id)

            if "groups" in group:
                self._sync_parent_relationships(group["groups"], current_group.id)

    def _ensure_parent_relationship(self, group_name, parent_id):
        group_id = self.existing_groups[group_name].id
        if parent_id not in self.group_parent_map.get(group_id, []):
            self._add_members_to_group(parent_id, [group_id])
            logger.info(f"Updated parent relationship: {group_name} -> {parent_id}")

    def _remove_from_parent(self, group_id, parent_id):
        member_values = [{"value": group_id}]
        self.client.groups.patch(
            id=parent_id,
            schemas=[iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP],
            operations=[
                iam.Patch(op=iam.PatchOp.REMOVE, path="members", value=member_values)
            ],
        )
        logger.info(f"Removed group {group_id} from parent {parent_id}")

    def _sync_users(self, groups):
        for group in groups:
            group_name = group["name"]
            group_id = self.existing_groups[group_name].id
            current_users = {
                m.value: m
                for m in self.client.groups.get(id=group_id).members
                if m.type == "user"
            }

            # Add missing users
            for user in group.get("users", []):
                user_id = self._create_user(user["name"], user["email"])
                if str(user_id) not in current_users:
                    self._add_members_to_group(group_id, [user_id])

            # Remove extra users
            expected_emails = {u["email"] for u in group.get("users", [])}
            for member in current_users.values():
                user = self.client.users.get(id=member.value)
                if user.user_name not in expected_emails:
                    self.client.groups.patch(
                        id=group_id,
                        schemas=[
                            iam.PatchSchema.URN_IETF_PARAMS_SCIM_API_MESSAGES_2_0_PATCH_OP
                        ],
                        operations=[
                            iam.Patch(
                                op=iam.PatchOp.REMOVE,
                                path="members",
                                value=[{"value": member.value}],
                            )
                        ],
                    )


# Rest of the original functions (create_user, add_members_to_group, etc.) remain same
# Main function updated to use GroupManager


def main():
    parser = argparse.ArgumentParser(
        description="Databricks account group synchronization tool"
    )
    parser.add_argument("yaml_file", help="Path to YAML structure definition")
    parser.add_argument(
        "--validate", action="store_true", help="Only validate structure"
    )
    args = parser.parse_args()

    client = AccountClient()
    manager = UserGroupManager(client)

    with open(args.yaml_file) as f:
        yaml_data = yaml.safe_load(f)

    if args.validate:
        report = manager.validate_structure(yaml_data["groups"])
        print("Validation Report:")
        print(f"Missing groups: {report['missing_groups']}")
        print(f"Extra groups: {report['extra_groups']}")
        print(f"Mismatched parents: {report['mismatched_parents']}")
    else:
        manager.sync_structure(yaml_data["groups"])
        logger.info("Synchronization completed successfully")


# if __name__ == "__main__":
#     main()
