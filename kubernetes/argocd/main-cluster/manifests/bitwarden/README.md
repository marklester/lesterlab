# Bitwarden offsite backup

`bitwarden-google-drive-backup` runs daily at **03:17 America/New_York**.
It stages a consistent SQLite backup plus attachments and Sends, then encrypts
and uploads them to Google Drive at `backups/bitwarden` using Restic and Rclone.
Retention: **7 daily, 4 weekly, 6 monthly snapshots**. Each run checks the repository.

The job uses a Python staging container and `tofran/restic-rclone:0.19.1_1.75.1`;
no packages are installed at runtime.

## Setup

Create a [Google OAuth Desktop client](https://rclone.org/drive/#making-your-own-client-id)
with the Drive API enabled and consent app published. Run `rclone config` to
create a `gdrive` remote using that client and the `drive.file` scope.

Store these keys with version `v1` in the `main-secret-store` backing data:

| Key | Value |
| --- | --- |
| `rclone/bitwarden-google-drive/client-id` | OAuth client ID |
| `rclone/bitwarden-google-drive/client-secret` | OAuth client secret |
| `rclone/bitwarden-google-drive/token` | Complete Rclone token JSON |
| `restic/main-backups/password` | Existing Restic password |

Keep credentials private and a recovery copy of the Restic password outside the cluster.

## Run manually

Once the ExternalSecret is ready:

```sh
kubectl --context main-cluster -n bitwarden get externalsecret bitwarden-google-drive-backup
kubectl --context main-cluster -n bitwarden create job bitwarden-google-drive-test --from=cronjob/bitwarden-google-drive-backup
kubectl --context main-cluster -n bitwarden logs -f job/bitwarden-google-drive-test -c backup
```

For staging failures, check the same job's logs with `-c stage`.

## Restore

With the same Restic and Rclone environment variables configured:

```sh
restic snapshots
restic restore latest --target /tmp/bitwarden-restore-test
sqlite3 /tmp/bitwarden-restore-test/stage/data/db.sqlite3 'PRAGMA quick_check;'
```

Stop Vaultwarden, copy the restored `stage/data/` contents into an empty `/data`
directory, then restart it. Do not reuse an old SQLite WAL file.

SQLite backups are consistent; attachments and Sends may change during copying.
Pause writes if these must match exactly. Test restores periodically.
