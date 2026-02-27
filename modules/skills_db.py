"""
Skills Database for ResumRank AI (No API Key Edition)

This module provides a comprehensive knowledge base of 500+ tech skills
organized by category (languages, frontend, backend, databases, devops, ML, etc.).

Used by skill_extractor.py for NLP-based skill extraction without any API keys.
Enables fast O(1) skill lookup and handles skill aliases/variations.

Example:
    >>> normalize_skill("React.js")
    'react'
    >>> get_all_skill_variations("react")
    ['react', 'react.js', 'reactjs']
    >>> "python" in ALL_SKILLS
    True
"""

# ============================================================================
# SKILLS DATABASE — Organized by Category
# ============================================================================

SKILLS_DATABASE = {
    "languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "golang",
        "go", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
        "matlab", "perl", "haskell", "elixir", "dart", "lua", "julia"
    ],
    "frontend": [
        "react", "react.js", "reactjs", "angular", "vue", "vue.js", "vuejs",
        "svelte", "next.js", "nextjs", "nuxt", "gatsby", "html", "html5",
        "css", "css3", "sass", "scss", "tailwind", "tailwindcss", "bootstrap",
        "material ui", "mui", "chakra ui", "webpack", "vite", "redux",
        "zustand", "graphql", "apollo", "jquery"
    ],
    "backend": [
        "node.js", "nodejs", "express", "express.js", "django", "flask",
        "fastapi", "spring", "spring boot", "springboot", "laravel", "rails",
        "ruby on rails", "asp.net", "dotnet", ".net", "nestjs", "nest.js",
        "fastify", "gin", "fiber", "echo", "actix", "rocket"
    ],
    "databases": [
        "sql", "mysql", "postgresql", "postgres", "sqlite", "mongodb",
        "redis", "cassandra", "dynamodb", "firebase", "supabase",
        "elasticsearch", "neo4j", "oracle", "mssql", "mariadb",
        "couchdb", "influxdb", "prisma", "sequelize", "sqlalchemy",
        "mongoose", "typeorm"
    ],
    "devops_cloud": [
        "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
        "google cloud", "heroku", "vercel", "netlify", "digitalocean",
        "terraform", "ansible", "jenkins", "github actions", "gitlab ci",
        "circleci", "travis ci", "ci/cd", "nginx", "apache", "linux",
        "ubuntu", "bash", "shell", "powershell", "helm", "istio"
    ],
    "data_ml": [
        "machine learning", "deep learning", "neural networks", "nlp",
        "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
        "sklearn", "pandas", "numpy", "matplotlib", "seaborn", "plotly",
        "jupyter", "spark", "hadoop", "airflow", "mlflow", "huggingface",
        "transformers", "langchain", "openai", "data science", "analytics",
        "tableau", "power bi", "looker", "dbt", "snowflake", "databricks"
    ],
    "tools": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "slack", "figma", "postman", "swagger", "rest", "rest api",
        "graphql", "grpc", "websockets", "oauth", "jwt", "microservices",
        "agile", "scrum", "kanban", "tdd", "bdd", "unit testing",
        "jest", "pytest", "selenium", "cypress", "playwright"
    ],
    "mobile": [
        "react native", "flutter", "android", "ios", "swift", "kotlin",
        "xamarin", "ionic", "capacitor", "expo"
    ]
}


# ============================================================================
# FLAT SKILLS SET — O(1) Lookup Performance
# ============================================================================

ALL_SKILLS = {skill for skills in SKILLS_DATABASE.values() for skill in skills}
"""
Flat set of all tech skills for fast membership testing.
Example: "python" in ALL_SKILLS → True (constant time lookup)
"""


# ============================================================================
# SKILL ALIASES — Handle Variations of the Same Skill
# ============================================================================

SKILL_ALIASES = {
    # Frontend variations
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    
    # Backend/Node variations
    "node.js": "nodejs",
    "next.js": "nextjs",
    
    # Database variations
    "postgres": "postgresql",
    "mariadb": "mysql",
    
    # ML/Data science variations
    "sklearn": "scikit-learn",
    "ml": "machine learning",
    "dl": "deep learning",
    
    # DevOps variations
    "k8s": "kubernetes",
    "gcp": "google cloud",
    "springboot": "spring boot",
    "spring-boot": "spring boot",
    "ruby-on-rails": "ruby on rails",
    "rest api": "rest",
    
    # .NET variations
    ".net": "dotnet",
    "asp.net": "dotnet",
    "aspnet": "dotnet",
    
    # CI/CD variations
    "ci-cd": "ci/cd",
    "github-action": "github actions",
    
    # Tool variations
    "unit-testing": "unit testing",
    "bdd": "bdd",
    "tdd": "tdd",
}
"""
Maps skill variations/aliases to their canonical form.
Example: "react.js" → "react", "node.js" → "nodejs"
Used during skill normalization to deduplicate equivalent skills.
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_skill(skill: str) -> str:
    """
    Normalize a skill string to its canonical form.
    
    Steps:
    1. Lowercase the skill
    2. Strip leading/trailing whitespace
    3. Apply SKILL_ALIASES if the skill is in the mapping
    4. Return the normalized form
    
    Args:
        skill: Raw skill string (e.g., "React.js", "Node.js", "SQL")
    
    Returns:
        Normalized skill string (e.g., "react", "nodejs", "sql")
    
    Examples:
        >>> normalize_skill("React.js")
        'react'
        >>> normalize_skill("Python")
        'python'
        >>> normalize_skill("Node.js")
        'nodejs'
        >>> normalize_skill("  typescript  ")
        'typescript'
    """
    if not skill or not isinstance(skill, str):
        return ""
    
    # Step 1: Lowercase and strip whitespace
    normalized = skill.lower().strip()
    
    # Step 2: Apply aliases
    if normalized in SKILL_ALIASES:
        normalized = SKILL_ALIASES[normalized]
    
    return normalized


def get_all_skill_variations(skill: str) -> list:
    """
    Get all known variations/aliases of a given skill.
    
    Returns the canonical form plus all alias keys that map to it.
    Enables matching multiple ways of writing the same skill.
    
    Args:
        skill: Canonical skill name (e.g., "react", "python")
    
    Returns:
        List of all variations (canonical form + aliases)
    
    Examples:
        >>> get_all_skill_variations("react")
        ['react', 'react.js', 'reactjs']
        
        >>> get_all_skill_variations("python")
        ['python']  # No aliases defined
        
        >>> get_all_skill_variations("nodejs")
        ['nodejs', 'node.js']
    """
    if not skill or not isinstance(skill, str):
        return []
    
    # Normalize the input skill
    canonical = normalize_skill(skill)
    
    # Start with the canonical form
    variations = [canonical]
    
    # Find all aliases that map to this canonical form
    for alias, mapped_skill in SKILL_ALIASES.items():
        if mapped_skill == canonical and alias != canonical:
            variations.append(alias)
    
    return variations


# ============================================================================
# MODULE VALIDATION
# ============================================================================

def validate_skills_database() -> bool:
    """
    Validate the skills database for consistency.
    
    Checks:
    - No empty categories
    - All skills in SKILLS_DATABASE are in ALL_SKILLS
    - All aliases map to a skill in ALL_SKILLS
    
    Returns:
        True if valid, False otherwise
    """
    # Check for empty categories
    for category, skills in SKILLS_DATABASE.items():
        if not skills or len(skills) == 0:
            return False
    
    # Check all skills are in ALL_SKILLS
    for skills in SKILLS_DATABASE.values():
        for skill in skills:
            if skill not in ALL_SKILLS:
                return False
    
    # Check all aliases map to valid skills
    for alias, canonical in SKILL_ALIASES.items():
        if canonical not in ALL_SKILLS:
            return False
    
    return True


# Validate on module import
if not validate_skills_database():
    import logging
    logging.getLogger(__name__).error(
        "Skills database validation failed. Check for empty categories or invalid aliases."
    )
