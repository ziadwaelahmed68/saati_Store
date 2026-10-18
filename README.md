# 🛒 SAATI WATCHES | Secure Cloud Architecture & DevSecOps Pipeline

![Saati Watches Architecture Diagram](images/image_bf8580.png)

A high-performance, secure, enterprise-grade e-commerce platform (**SAATI WATCHES**) designed for luxury timepiece retail. The platform is engineered using a decoupled **Microservices Architecture** on **Amazon Web Services (AWS)** in the **Frankfurt (`eu-central-1`)** region, incorporating modern **DevSecOps** practices, automated threat scanning, container signing, and zero-downtime rolling deployments.

---

## 🎨 0. Frontend UI & Live Application Preview

The platform provides a responsive, fast, and modern web user interface serving customers globally via CloudFront edge locations.

![Saati Watches Live Frontend Application](images/frontend_preview.png)

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

![VPC Setup](images/vpc.jpg)
![Subnets](images/subnets.jpg)
![Internet Gateway](images/igw.jpg)
![Route Table](images/rt.jpg)

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

![Load Balancer](images/lb.jpg)
![Target Groups](images/tg.jpg)

Traffic distribution is managed by an **Application Load Balancer (`saati-alb`)**, listening on port `HTTP:80` and forwarding requests evenly (25% weight allocation) across specialized Target Groups.

| Target Group Name | Port | Protocol | Service Function | Target Type |
| :--- | :--- | :--- | :--- | :--- |
| **`saati-auth-tg`** | `8081` | HTTP | Handles user auth, JWT validation, & Cognito sessions | IP |
| **`saati-products-tg`** | `8082` | HTTP | Serves watch inventory, details, and metadata | IP |
| **`saati-images-tg`** | `8083` | HTTP | Handles media processing and product image lookups | IP |
| **`saati-orders-tg`** | `8084` | HTTP | Processes transactions, order state, and checkout flows | IP |

---

## 🔄 4. CloudFront CDN & Path Behaviors

![CloudFront General](images/cloudfront.jpg)
![CloudFront Origins](images/origin%20cloud%20.jpg)
![CloudFront Behaviors](images/behiver%20cloud%20.jpg)

The **`saati-store`** CloudFront Distribution (`d28bzg8arlab4ye.cloudfront.net`) operates with 3 origins protected by **Origin Access Control (OAC)** to enforce secure access.

### 📌 Path Behavior Rules:
1. `/api/*` ➔ Origin: **`saati-alb`** | Caching: **Disabled** (`CachingDisabled`) | Viewer Policy: Redirect HTTP to HTTPS.
2. `/products/*` ➔ Origin: **`saati-images-bucket`** | Caching: **Optimized** (`CachingOptimized`) | Viewer Policy: Redirect HTTP to HTTPS.
3. `Default (*)` ➔ Origin: **`saati-bucket`** | Caching: **Optimized** (`CachingOptimized`) | Serves `index.html` as Default Root Object.

---

## 🐳 5. Containerized Microservices (ECS Fargate Cluster)

![ECS Cluster](images/cluster.jpg)
![Task Definitions](images/task%20definition.jpg)
![Running Tasks](images/task%20cluster.jpg)
![Auth Task](images/auth%20task.jpg)
![Products Task](images/proudact%20task.jpg)
![Images Task](images/images%20task.jpg)
![Orders Task](images/task%20orders.jpg)

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

![S3 Frontend Bucket](images/s3%20bucket.jpg)
![S3 Images Bucket](images/images.jpg)
![ECR Repositories](images/esr.jpg)
![DynamoDB Tables](images/dynamodb.jpg)

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

![Saati Watches Store Front Page](images/frontend_home.png)
![Saati Watches Product Details Page](images/frontend_product.png)

---

## 👤 Project Author & Cloud Engineer
* **Name:** Mohamed Mostafa Abdelgawad Khalifa
* **Role:** Cloud Infrastructure & DevSecOps Engineer
