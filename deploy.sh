#!/bin/bash
set -euo pipefail

###############################################################################
# deploy.sh — Build & deploy KRISE to AWS (ECR + S3 + App Runner)
###############################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# ── AWS config ──────────────────────────────────────────────────────────────
AWS_ACCOUNT_ID="571944666798"
AWS_REGION="us-east-1"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
ECR_REPO="krise"
BACKEND_TAG="backend"
S3_BUCKET="krise-frontend-571944666798"
APPRUNNER_URL="https://yarnm75uey.us-east-1.awsapprunner.com"

# Load AWS credentials from backend/.env if not already in environment
if [ -z "${AWS_ACCESS_KEY_ID:-}" ] && [ -f "$SCRIPT_DIR/backend/.env" ]; then
    echo "📦 Loading AWS credentials from backend/.env ..."
    set -a
    source "$SCRIPT_DIR/backend/.env"
    set +a
fi

# ── Functions ───────────────────────────────────────────────────────────────
ecr_login() {
    echo "🔑 Logging into ECR ..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$ECR_REGISTRY"
}

deploy_backend() {
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  🐳 Building & pushing backend image"
    echo "══════════════════════════════════════════════════════════"

    ecr_login

    docker build -t "${ECR_REPO}:${BACKEND_TAG}" "$SCRIPT_DIR/backend"
    docker tag "${ECR_REPO}:${BACKEND_TAG}" "${ECR_REGISTRY}/${ECR_REPO}:${BACKEND_TAG}"
    docker push "${ECR_REGISTRY}/${ECR_REPO}:${BACKEND_TAG}"

    echo "✅ Backend image pushed: ${ECR_REGISTRY}/${ECR_REPO}:${BACKEND_TAG}"
    echo ""
    echo "⚠️  IMPORTANT: Go to the AWS Console → App Runner → Krise → Deploy"
    echo "   to trigger a redeployment with the new image."
}

deploy_frontend() {
    echo ""
    echo "══════════════════════════════════════════════════════════"
    echo "  🌐 Building & deploying frontend to S3"
    echo "══════════════════════════════════════════════════════════"

    cd "$SCRIPT_DIR/frontend"

    echo "📦 Installing dependencies ..."
    npm ci --silent

    echo "🔨 Building with VITE_API_URL=${APPRUNNER_URL} ..."
    VITE_API_URL="$APPRUNNER_URL" npm run build

    echo "🚀 Syncing dist/ to s3://${S3_BUCKET} ..."
    aws s3 sync dist/ "s3://${S3_BUCKET}" --delete --region "$AWS_REGION"

    echo "✅ Frontend deployed to: http://${S3_BUCKET}.s3-website-${AWS_REGION}.amazonaws.com"
    cd "$SCRIPT_DIR"
}

# ── Main ────────────────────────────────────────────────────────────────────
usage() {
    echo "Usage: ./deploy.sh [backend|frontend|all]"
    echo ""
    echo "  backend   Build Docker image & push to ECR"
    echo "  frontend  Build Vue app & sync to S3"
    echo "  all       Deploy both (default)"
}

TARGET="${1:-all}"

case "$TARGET" in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    all)
        deploy_backend
        deploy_frontend
        ;;
    -h|--help)
        usage
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        usage
        exit 1
        ;;
esac

echo ""
echo "🎉 Deployment complete!"
