# 🛒 SAATI WATCHES | Secure Cloud Architecture & DevSecOps Pipeline




![Saati Watches Architecture Diagram](https://github.com/user-attachments/assets/898469a5-1b86-4fee-8deb-0d3f78d3cd6e)

A high-performance, secure, enterprise-grade e-commerce platform (**SAATI WATCHES**) designed for luxury timepiece retail. The platform is engineered using a decoupled **Microservices Architecture** on **Amazon Web Services (AWS)** in the **Frankfurt (`eu-central-1`)** region, incorporating modern **DevSecOps** practices, automated threat scanning, container signing, and zero-downtime rolling deployments.

---

## 🎨 0. Frontend UI & Live Application Preview

The platform provides a responsive, fast, and modern web user interface serving customers globally via CloudFront edge locations.

![Saati Watches Live Frontend Application](https://github.com/user-attachments/assets/0744b3e2-831b-4d8b-944f-14c7b8d60439)
![Saati Watches Live Frontend Application](https://github.com/user-attachments/assets/e997bc69-ceaa-49b7-9e3d-1eb3c7017514)



### 🌟 Key End-User Features:
* **Interactive Catalog & Showcase:** Real-time watch catalog rendering powered by CloudFront CDN and cached S3 static assets (`index.html`, `app.js`, `style.css`).
* **Secure Authentication Flow:** Seamless user registration, sign-in, and session management integrated with **Amazon Cognito User Pools** and JWT validation.
* **High-Speed Asset Delivery:** High-resolution product images served with minimal latency via **Amazon CloudFront** using **Origin Access Control (OAC)**.
* **Dynamic Checkout & Order Tracking:** Interactive shopping cart, order placement, and live status tracking backed by serverless NoSQL tables on **Amazon DynamoDB**.

---

## 📐 1. Cloud Architecture & Design Overview

The architecture follows strict AWS Well-Architected Framework guidelines, emphasizing operational excellence, security, reliability, performance efficiency, and cost optimization.

### 🔍 System Component Breakdown:
* **Edge & Delivery Layer:** **Amazon CloudFront** acts as the primary global entry point, caching static web resources and proxying API traffic directly to backend services.
* **Security & Perimeter Layer:** **AWS WAF** shields the application against web exploits (XSS, SQL Injection) and rate-limits traffic before reaching the load balancer.
* **Compute Layer:** **Amazon ECS on AWS Fargate** hosts isolated containerized microservices across multiple Availability Zones without managing EC2 instances.
* **Data & Storage Layer:** **Amazon DynamoDB** handles fast key-value data queries for users, products, and orders, while **Amazon S3** stores application source code and media.

---

## 🌐 2. VPC & Networking Infrastructure

![VPC Setup](https://github.com/user-attachments/assets/5a09b7fd-2486-4bfd-a373-2e42b42a2f16)


![Subnets](https://github.com/user-attachments/assets/eaa76c4f-c135-4274-a5e4-86e4e2cf67cb)


![Internet Gateway](https://github.com/user-attachments/assets/5f74571f-167e-43da-bc19-8418a625e412)


![Route Table](https://github.com/user-attachments/assets/8bec0594-954a-4cbc-b5b8-dfdb4e6dd86d)



The network perimeter is isolated inside a custom Virtual Private Cloud (**VPC**) configured across 3 Availability Zones (`eu-central-1a`, `eu-central-1b`, `eu-central-1c`) to achieve high availability and fault tolerance.

### 🛠 Network Configuration Details:
* **VPC Name & ID:** `saati-vpc` (`vpc-0b8769a1e305989a8`)
* **Internet Gateway:** `saati-igw` (`igw-0816d37006ff3667f`) providing external routing.
* **Route Table:** `saati-RT` (`rtb-05e80b3cdf68ecc75`)
* **Subnets Distribution:**
  * `saati-sub-1` (`10.0.1.0/24`) – Availability Zone A
  * `saati-sub-2` (`10.0.2.0/24`) – Availability Zone B
  * `saati-sub-3` (`10.0.3.0/24`) – Availability Zone C

---

## ⚖️ 3. Load Balancing & Traffic Routing

![Load Balancer](https://github.com/user-attachments/assets/f18cacb7-3528-4ffd-97ab-33135fab9b26)


![Target Groups](https://github.com/user-attachments/assets/34d0f939-4b88-413f-ada8-a4aadebacb95)



Traffic distribution is managed by an **Application Load Balancer (`saati-alb`)**, listening on port `HTTP:80` and forwarding requests evenly (25% weight allocation) across specialized Target Groups.

| Target Group Name | Port | Protocol | Service Function | Target Type |
| :--- | :--- | :--- | :--- | :--- |
| **`saati-auth-tg`** | `8081` | HTTP | Handles user auth, JWT validation, & Cognito sessions | IP |
| **`saati-products-tg`** | `8082` | HTTP | Serves watch inventory, details, and metadata | IP |
| **`saati-images-tg`** | `8083` | HTTP | Handles media processing and product image lookups | IP |
| **`saati-orders-tg`** | `8084` | HTTP | Processes transactions, order state, and checkout flows | IP |

---

## 🔄 4. CloudFront CDN & Path Behaviors

![CloudFront General](https://github.com/user-attachments/assets/b5bcc1bd-47a1-4771-bf82-14cc59c4bc40)


![CloudFront Origins](https://github.com/user-attachments/assets/635a1fcd-ceca-4ce5-818c-f3f17c640140)


![CloudFront Behaviors](https://github.com/user-attachments/assets/fbd16be1-9cdb-4fa0-a0b1-21b6ad589f17)



The **`saati-store`** CloudFront Distribution (`d28bzg8arlab4ye.cloudfront.net`) operates with 3 origins protected by **Origin Access Control (OAC)** to enforce secure access.

### 📌 Path Behavior Rules:
1. `/api/*` ➔ Origin: **`saati-alb`** | Caching: **Disabled** (`CachingDisabled`) | Viewer Policy: Redirect HTTP to HTTPS.
2. `/products/*` ➔ Origin: **`saati-images-bucket`** | Caching: **Optimized** (`CachingOptimized`) | Viewer Policy: Redirect HTTP to HTTPS.
3. `Default (*)` ➔ Origin: **`saati-bucket`** | Caching: **Optimized** (`CachingOptimized`) | Serves `index.html` as Default Root Object.

---

## 🐳 5. Containerized Microservices (ECS Fargate Cluster)

![ECS Cluster](https://github.com/user-attachments/assets/c49104bf-702a-4396-89f0-4fccb57a625f)


![Task Definitions](https://github.com/user-attachments/assets/3c2e3cda-bfaa-4f6e-a69c-4afad8554d72)


![Running Tasks](https://github.com/user-attachments/assets/d9867df9-26b5-4dab-90c4-170716cc8c37)


![Auth Task](https://github.com/user-attachments/assets/f7d8b476-8040-4fb1-8fc4-065b7468c74a)


![Products Task](https://github.com/user-attachments/assets/0b0c4d40-9dae-458d-9d9a-de2dbcde8fd2)


![Images Task](https://github.com/user-attachments/assets/ead8e50e-ea2f-4b05-9eac-8b73cc30408a)


![Orders Task](https://github.com/user-attachments/assets/3d680c68-ebf9-4ca0-a03c-cb4aced19f5a)



All backend microservices run serverlessly on **AWS Fargate** within the **`saati-store-cluster`**, isolated using `awsvpc` networking mode and running on `Linux/X86_64` architecture.

### ⚙️ Detailed Task Specifications:

#### 1. Auth Service (`saati-auth-task:9`)
* **Resources:** `0.25 vCPU` (256 units) | `512 MiB Memory`
* **Environment Configuration:**
  * `AUTH_PROVIDER`: `cognito`
  * `COGNITO_CLIENT_ID`: `6eb8pmda390b2mifetmfrha2gv`
  * `COGNITO_USER_POOL_ID`: `eu-central-1_61kHuKfU3`
  * `AUTH_SECRET_KEY`: `saati-prod-super-secret-hmac-key-2026`
  * `PORT`: `8081`

#### 2. Products Service (`saati-products-task:5`)
* **Resources:** `0.25 vCPU` (256 units) | `512 MiB Memory`
* **Environment Configuration:**
  * `PORT`: `8082`
  * `PRODUCTS_TABLE`: `saati_products`
  * `S3_BUCKET_NAME`: `saati-images-bucket`
  * `CLOUDFRONT_DOMAIN`: `d28bzg8arlab4ye.cloudfront.net`
  * `AUTH_SECRET_KEY`: `saati-prod-super-secret-hmac-key-2026`

#### 3. Images Service (`saati-images-task:4`)
* **Resources:** `0.25 vCPU` (256 units) | `512 MiB Memory`
* **Environment Configuration:**
  * `PORT`: `8083`
  * `S3_BUCKET_NAME`: `saati-images-bucket`
  * `CLOUDFRONT_DOMAIN`: `d28bzg8arlab4ye.cloudfront.net`
  * `AUTH_SECRET_KEY`: `saati-prod-super-secret-hmac-key-2026`

#### 4. Orders Service (`saati-orders-task:5`)
* **Resources:** `0.25 vCPU` (256 units) | `512 MiB Memory`
* **Environment Configuration:**
  * `PORT`: `8084`
  * `ORDERS_TABLE`: `saati_orders`
  * `PRODUCTS_TABLE`: `saati_products`
  * `AUTH_SECRET_KEY`: `saati-prod-super-secret-hmac-key-2026`

---

## 🗄️ 6. Database Schema, S3 Buckets & Container Registry

![S3 Frontend Bucket](https://github.com/user-attachments/assets/1a40a421-8a21-487b-9bc6-f36b754de416)

![S3 Images Bucket](https://github.com/user-attachments/assets/c3cf4ccc-ba16-4b4f-978f-ddf2fd4bd395)

![DynamoDB Tables](https://github.com/user-attachments/assets/e97c1541-7110-42e8-a8c6-3b4e7ad9eea7)



### 📊 Amazon DynamoDB Schema:
* **`saati_users`:** Key Schema: `email (S)` [Partition Key] – Stores user profiles & authorization metadata.
* **`saati_products`:** Key Schema: `productId (S)` [Partition Key] – Contains watch specifications, pricing, and stock status.
* **`saati_orders`:** Key Schema: `orderId (S)` [Partition Key] – Tracks customer orders, items, and fulfillment state.

### 📦 S3 Storage & ECR Repositories:
* **`saati-bucket`:** Stores static frontend web files (`index.html`, `app.js`, `style.css`, `config.js`).
* **`saati-images-bucket`:** Stores watch image assets inside the `/products/` folder hierarchy.
* **Amazon ECR Repositories:** Encrypted private container repositories (`saati-auth`, `saati-images`, `saati-orders`, `saati-products`) backed by AES-256 encryption.

---

## 🔒 7. Automated DevSecOps Pipeline

The deployment process implements a **Security-First (DevSecOps)** approach automated via **GitHub Actions** across two dedicated workflows:

### A. Continuous Integration Pipeline (CI - `develop` branch / Pull Requests):
1. **Secret Scanning (`Gitleaks`):** Inspects codebase for leaked credentials, private keys, or API tokens.
2. **Software Composition Analysis (`Trivy`):** Scans container dependencies and packages for `CRITICAL` or `HIGH` vulnerabilities.
3. **Static Application Security Testing (`Semgrep`):** Analyzes source code for security anti-patterns and code flaws.
4. **Unit Testing (`Pytest`):** Validates business logic and function execution.
5. **Artifact Upload:** Archives security reports for compliance review.

### B. Continuous Deployment Pipeline (CD - `main` branch):
1. **OIDC Authentication (`AWS IAM Role`):** Establishes passwordless authentication between GitHub and AWS (no hardcoded credentials).
2. **Docker Build, Push & Signing (`Cosign`):** Builds container images, pushes them to **Amazon ECR**, and cryptographically signs images.
3. **Frontend Sync & Cache Invalidation:** Synchronizes static files to **Amazon S3** and purges **CloudFront** edge locations.
4. **Dynamic Security Testing (`OWASP ZAP`):** Performs runtime DAST vulnerability scans against active API endpoints.
5. **ECS Rolling Deployment:** Executes zero-downtime rolling updates to update ECS Fargate tasks seamlessly.

---

## 🖼️ 8. Final Application Showcase

Below is the complete user journey from landing on the storefront to reviewing products and managing orders:



![Saati Watches Product Details Page](https://github.com/user-attachments/assets/cf3ff2e4-603a-4c6f-ae67-7535f25466f8)


![Saati Watches Product Details Page](https://github.com/user-attachments/assets/ad4f4f00-8528-4ad1-b62a-ae942c5cb3ba)

![Saati Watches Product Details Page](https://github.com/user-attachments/assets/55540397-1171-4106-9371-85a361e9eb2b)


---


## 👥 Project Team & Cloud Engineering

### Team Members

1. **Mohamed Mostafa** 
2. **Zeyad Wael**
3. **Sameh Mohamed**
4. **Ahmed Ehab**
5. **Samia Samy**

### Specialization
Cloud Infrastructure, DevSecOps, and Cloud Security

