* confirm: put logs for tunnar and mellishearc there
  confirm: same for plex get the non stdout logs

* setup plex 
* create a tunarr mcp

* setup alerts for
    * os upgrades
    * k8s upgrades
    * failing backing ups
    * hdds down

* check if k8s upgrades are working
* setup up os upgrades
* offsite backup for personal secrets

* upgrade to 1.20 ceph
  * todo move away for nfs and use ceph directly
    * convert nfs use to straight cephfs use:
      Bazarr	manifests/bazarr/deployment.yml
      Home Assistant	manifests/home-assistant/home-assistant-deployment.yaml
      Lidarr	manifests/lidarr/lidarr.deployment.yaml
      Plex	manifests/plex/plex.deployment.yaml
      qBittorrent	manifests/qbittorrent/qbittorrent.deployment.yaml
      Radarr	manifests/radarr/radarr.deployment.yaml
      Sonarr	manifests/sonarr/sonarr.deployment.yaml
      Soulseek	manifests/soulseek/soulseek.deployment.yaml
  * wait for key encryption to be fixed

* fix local certs

* see if we can make home-assistant more useful with an mcp
  * create automations with opencode or chat



