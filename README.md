# k8s-gitops-platform — GitOps Delivery Platform on Kubernetes

A complete GitOps pipeline where merging to a branch is the deployment. ArgoCD watches the repo, any change to a manifest automatically syncs to the cluster. Built to demonstrate declarative infrastructure, multi-environment promotion, and real observability — all at zero cloud cost.

[![Status](https://img.shields.io/badge/Status-In%20Progress-blue)]()
[![Platform](https://img.shields.io/badge/Platform-Kubernetes%20k3s-326CE5)]()
[![GitOps](https://img.shields.io/badge/GitOps-ArgoCD-EF7B4D)]()
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitLab%20CI-FC6D26)]()
[![Packaging](https://img.shields.io/badge/Packaging-Helm-0F1689)]()
[![Observability](https://img.shields.io/badge/Observability-Prometheus%20%2B%20Grafana-F46800)]()
[![Cost](https://img.shields.io/badge/Cost-Free%20(local)-brightgreen)]()

---

## Stack

| Layer | Technology |
|---|---|
| Cluster | k3s (local, single-node) |
| GitOps controller | ArgoCD |
| App packaging | Helm |
| CI/CD | GitLab CI |
| Container registry | GitLab Container Registry |
| Ingress | NGINX Ingress Controller |
| Metrics | Prometheus (kube-prometheus-stack) |
| Dashboards | Grafana |
| Application | Python FastAPI |
| Language | Python 3.11 |

---

## Phases

- [ ] Phase 1 — Local cluster bootstrap (k3s + ArgoCD)
- [ ] Phase 2 — Application + Helm chart
- [ ] Phase 3 — GitOps wiring (ArgoCD Applications, dev + prod)
- [ ] Phase 4 — CI/CD pipeline (GitLab CI)
- [ ] Phase 5 — Observability (Prometheus + Grafana)
- [ ] Phase 6 — Security hardening
- [ ] Phase 7 — Documentation + EKS path

---

## Architecture

```
GitLab push (main)
        │
        ▼
GitLab CI Pipeline
  ├── test        — pytest
  ├── build       — docker build
  ├── push        — registry.gitlab.com/<user>/k8s-gitops-platform/demo-api:<git-sha>
  └── update-tag  — commits new image.tag → manifests/envs/dev/values.yaml
        │
        ▼
ArgoCD (running in cluster, polling this repo)
  ├── Detects drift in manifests/envs/dev/
  └── Syncs to k3s cluster automatically
        │
        ▼
k3s Cluster
  ├── Namespace: dev
  │     ├── Deployment  (demo-api, 1 replica)
  │     ├── Service     (ClusterIP)
  │     └── Ingress     (NGINX)
  ├── Namespace: prod
  │     ├── Deployment  (demo-api, 2 replicas)
  │     ├── Service     (ClusterIP)
  │     └── Ingress     (NGINX)
  └── Namespace: monitoring
        ├── Prometheus
        └── Grafana
```

Traffic: `Client → NGINX Ingress → Service → Pod`  
No direct pod access. All traffic routed through the ingress controller.

---

## Folder Structure

```
k8s-gitops-platform/
│
├── app/                              # Application source
│   ├── main.py                       # FastAPI — /health, /info, /items
│   ├── requirements.txt
│   └── Dockerfile
│
├── charts/                           # Helm chart
│   └── demo-api/
│       ├── Chart.yaml
│       ├── values.yaml               # Base defaults
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── ingress.yaml
│           └── serviceaccount.yaml
│
├── manifests/                        # ArgoCD watches this
│   ├── argocd/
│   │   ├── project.yaml              # AppProject (RBAC boundary)
│   │   ├── app-dev.yaml              # ArgoCD Application → dev
│   │   └── app-prod.yaml             # ArgoCD Application → prod
│   └── envs/
│       ├── dev/
│       │   └── values.yaml           # image.tag auto-updated by CI
│       └── prod/
│           └── values.yaml           # image.tag promoted manually
│
├── monitoring/
│   ├── prometheus-values.yaml        # kube-prometheus-stack overrides
│   └── grafana-dashboard.json        # App dashboard (loaded via ConfigMap)
│
├── .gitlab-ci.yml                    # Pipeline definition
│
├── docs/
│   ├── local-setup.md
│   └── eks-path.md                   # EKS production path (documented, not deployed)
│
└── README.md
```

---

## The Application — `demo-api`

A lightweight FastAPI service with real Prometheus metrics. Enough to generate meaningful dashboards without distracting from the platform.

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe — `{"status": "ok"}` |
| GET | `/info` | App version, environment name, pod hostname |
| GET | `/items` | Returns a mock item list (simulates read load) |
| POST | `/items` | Accepts JSON body, returns it with a generated ID |

`prometheus-fastapi-instrumentator` auto-exposes `/metrics` — request count, latency histograms, error rates per endpoint. Prometheus scrapes this. Grafana dashboards it.

---

## Environments

| Environment | Namespace | Replicas | Deploy trigger |
|---|---|---|---|
| dev | `dev` | 1 | Automatic — every push to `main` |
| prod | `prod` | 2 | Manual — `promote` job in GitLab CI UI |

Same Helm chart, different `values.yaml` per environment. The only difference is the image tag and replica count.

---

## CI/CD Pipeline

```
test → build → push → update-tag → (manual) promote
```

| Stage | What it does |
|---|---|
| `test` | pytest against the FastAPI app |
| `build` | `docker build` |
| `push` | Push to GitLab Container Registry, tag = `$CI_COMMIT_SHORT_SHA` |
| `update-tag` | Commit new `image.tag` to `manifests/envs/dev/values.yaml` |
| `promote` | Manual — copies dev image tag to `manifests/envs/prod/values.yaml` |

Secrets (`$CI_REGISTRY_USER`, `$CI_REGISTRY_PASSWORD`) injected via GitLab CI/CD variables — never in code, never in Git.

---

## FinOps Notes

Default setup costs **zero**:

- k3s runs locally — no cloud compute
- GitLab free tier covers CI minutes, container registry, and repo hosting
- ArgoCD, Prometheus, Grafana are open source

### EKS production path (documented in `docs/eks-path.md`, not deployed)

| Resource | Type | Est. Cost |
|---|---|---|
| EKS control plane | Managed | ~$0.10/hr |
| EC2 node (×1) | t3.small spot | ~$0.007/hr |
| **Total (idle)** | | **~$15–20/month** |

FinOps decisions for EKS path:
- **Spot instances** — 60–70% cheaper than on-demand for non-critical workloads
- **Single node group** — minimum viable cluster, scale up only when needed
- **`terraform destroy` runbook** — tear down after demos, no idle cost
- **No NAT Gateway** — public subnets with restricted SGs to avoid $0.045/hr NAT charge
- **GitLab registry** — avoids ECR costs ($0.10/GB/month) entirely

---

## Security Highlights

| Area | Implementation |
|---|---|
| ArgoCD scope | `AppProject` limits ArgoCD to specific namespaces and repos only |
| Container | Non-root UID (1000), read-only root filesystem, no privilege escalation |
| Resource limits | CPU + memory limits on all pods — no runaway resource consumption |
| Secrets | GitLab CI variables (masked + protected) — never in Git, never in image |
| Registry | GitLab Container Registry — private by default, scoped to project |
| RBAC | ArgoCD `ServiceAccount` has minimum required cluster permissions |
| Image tagging | Git SHA tags — no `latest` in production, full traceability |

---

## Workflow

### Step 1 — Bootstrap the cluster

```bash
# Install k3s
curl -sfL https://get.k3s.io | sh -

# Install ArgoCD
kubectl create namespace argocd
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd -n argocd

# Access ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

### Step 2 — Apply ArgoCD Applications

```bash
kubectl apply -f manifests/argocd/
```

ArgoCD takes ownership of `dev` and `prod` namespaces from this point.

### Step 3 — Trigger a deployment

Push any change to `main`. Watch in the ArgoCD UI:
1. GitLab CI runs — image built, pushed, tag committed
2. ArgoCD detects drift in `manifests/envs/dev/values.yaml`
3. ArgoCD syncs — new pod rolling out in `dev` namespace

### Step 4 — Promote to prod

In GitLab → CI/CD → Pipelines → run the `promote` job manually.  
ArgoCD detects the tag change in `manifests/envs/prod/values.yaml` and syncs prod.

### Step 5 — Check observability

```bash
kubectl port-forward svc/grafana -n monitoring 3000:3000
```

Open `http://localhost:3000` — dashboard shows request rate, error rate, p99 latency.

---

## Local Development

```bash
cd app
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
pip install -r requirements.txt
uvicorn main:app --reload
# http://127.0.0.1:8000
```

```bash
docker build -t demo-api .
docker run -p 8000:8000 demo-api
```

---

## API Reference

| Method | Endpoint | Body | Response |
|---|---|---|---|
| GET | `/health` | — | 200 + `{"status": "ok"}` |
| GET | `/info` | — | 200 + version, env, hostname |
| GET | `/items` | — | 200 + JSON array |
| POST | `/items` | `{"name": "..."}` | 201 + item with ID |
| GET | `/metrics` | — | Prometheus text format |

---

## Problems & Fixes

| Problem | Fix |
|---|---|
| *(populated as issues are encountered)* | |

---

## Things to Improve

- HTTPS on the ingress via cert-manager + Let's Encrypt
- HPA (Horizontal Pod Autoscaler) based on Prometheus custom metrics
- Loki log aggregation (currently Prometheus + Grafana only)
- Sealed Secrets or External Secrets Operator for in-cluster secret management
- Trivy image scanning stage in GitLab CI
- Renovate bot for automated Helm chart and image dependency updates
- GitLab webhooks to replace ArgoCD polling with push-based sync
- `multi-node` k3s setup to simulate real cluster scheduling

---

## Dev Environment

- OS: Windows, PowerShell
- Editor: VS Code
- Tools: Git, Docker, kubectl, Helm, k3s
- Accounts: GitLab (free tier)