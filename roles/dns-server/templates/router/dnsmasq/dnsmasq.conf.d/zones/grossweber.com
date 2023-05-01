cname=cloud.grossweber.com,                         router.home.therightstuff.de
cname=cr.grossweber.com,                            router.home.therightstuff.de
cname=gitea.grossweber.com,                         router.home.therightstuff.de
cname=gitlab.grossweber.com,                        router.home.therightstuff.de
cname=kibana.grossweber.com,                        router.home.therightstuff.de

# Kubernetes services.
cname=traefik.kube.lab.grossweber.com,                   kube.lab.grossweber.com
cname=argocd.kube.lab.grossweber.com,                    kube.lab.grossweber.com
cname=dashboard.kube.lab.grossweber.com,                 kube.lab.grossweber.com
cname=gw.kube.lab.grossweber.com,                        kube.lab.grossweber.com
cname=mail.gw.kube.lab.grossweber.com,                   kube.lab.grossweber.com
cname=seq.gw.kube.lab.grossweber.com,                    kube.lab.grossweber.com
