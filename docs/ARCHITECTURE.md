# API Builder - Architecture Documentation

## 🏗️ System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         User Layer                            │
├────────────────┬─────────────────┬─────────────────┬─────────┤
│      CLI       │    Web UI       │   API Gateway   │ Plugins │
│    (Typer)     │   (Future)      │    (Future)     │         │
└────────┬───────┴────────┬────────┴────────┬────────┴─────────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                    Orchestration Layer                        │
├──────────────────────────────────────────────────────────────┤
│                      QAPI Session Manager                     │
│  • Authentication  • State Management  • Error Handling       │
└──────┬────────────────────────────────────────────────────┬──┘
       │                                                    │
┌──────▼──────────────────────────────────────────────────▼────┐
│                     Intelligence Layer                        │
├───────────────┬────────────────┬──────────────┬──────────────┤
│  Dependency   │   Parameter    │  Execution   │   Natural    │
│   Analyzer    │    Detector    │   Planner    │   Language   │
└───────────────┴────────────────┴──────────────┴──────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────┐
│                      Parser Layer                             │
├───────────────┬────────────────┬──────────────┬──────────────┤
│   OpenAPI     │   Postman      │     LLM      │   Custom     │
│   Parser      │   Parser       │   Parser     │   Parsers    │
└───────────────┴────────────────┴──────────────┴──────────────┘
                                  │
┌─────────────────────────────────▼─────────────────────────────┐
│                       Data Layer                              │
├────────────────┬──────────────────────────┬──────────────────┤
│  Auto-Generated│   State Management       │   Configuration  │
│   API Client   │   (Encrypted Storage)    │   (.env, JSON)   │
└────────────────┴──────────────────────────┴──────────────────┘
```

## 🔧 Core Components

### 1. Parser System

**Purpose**: Convert various API documentation formats into a unified internal model.

```python
# Abstract interface for all parsers
class APIParser(Protocol):
    def parse(self, source: Any) -> APISpecification
    def validate(self, spec: APISpecification) -> List[ValidationError]
    def confidence_score(self) -> float
```

**Key Design Decisions**:
- **Strategy Pattern**: Each parser is a strategy implementation
- **Factory Pattern**: Parser selection based on input format
- **Chain of Responsibility**: Parsers can delegate to others

### 2. Dependency Analyzer

**Purpose**: Build a graph of parameter dependencies between endpoints.

```python
class DependencyAnalyzer:
    def analyze_parameters(self) -> Dict[str, List[str]]
    def build_dependency_graph(self) -> Dict[str, Set[str]]
    def get_execution_plan(self, target: str) -> List[str]
```

**Key Algorithms**:
- **Topological Sort**: Order endpoints by dependencies
- **Cycle Detection**: Identify circular dependencies
- **Graph Traversal**: Find optimal execution paths

### 3. Parameter Detector

**Purpose**: Intelligently identify parameter types and relationships.

```python
class ParameterDetector:
    def detect_parameter_type(self, name: str, schema: dict) -> ParameterInfo
    def is_foreign_key(self, param_name: str) -> bool
    def get_likely_provider(self, param_name: str) -> Optional[str]
```

**Detection Strategies**:
- **Pattern Matching**: Regex for common patterns (IDs, dates)
- **Schema Analysis**: Type and format from OpenAPI
- **Heuristics**: Naming conventions and context

### 4. Execution Planner

**Purpose**: Create optimized execution plans for API workflows.

```python
class ExecutionPlanner:
    def create_plan(self, goal: Goal) -> ExecutionPlan
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan
    def estimate_time(self, plan: ExecutionPlan) -> timedelta
```

**Optimization Techniques**:
- **Parallel Execution**: Identify independent calls
- **Caching**: Reuse previous results
- **Batching**: Combine similar requests

### 5. State Manager

**Purpose**: Persist application state securely.

```python
class StateManager:
    def save_token(self, token: str) -> None
    def save_credentials(self, email: str, password: str) -> None
    def save_context(self, context: Dict[str, Any]) -> None
    def get_command_history(self) -> List[Command]
```

**Security Features**:
- **Encryption**: Fernet symmetric encryption
- **Key Management**: Secure key generation and storage
- **Access Control**: File permissions and user isolation

## 🎨 Design Patterns

### Implemented Patterns

1. **Command Pattern**
   - Used in CLI command structure
   - Each command is an independent module
   - Enables undo/redo functionality

2. **Factory Pattern**
   - Parser creation based on input type
   - Client generation from OpenAPI spec
   - Adapter selection for output formats

3. **Strategy Pattern**
   - Different parsing strategies
   - Various authentication methods
   - Multiple execution strategies

4. **Observer Pattern**
   - Event system for plugin hooks
   - Progress tracking and notifications
   - State change notifications

5. **Facade Pattern**
   - QAPI Session as simplified interface
   - Hides complexity of client operations
   - Unified API for different backends

### Planned Patterns

1. **Chain of Responsibility**
   - Request preprocessing pipeline
   - Error handling chain
   - Plugin middleware system

2. **Decorator Pattern**
   - Request/response modifications
   - Caching layer
   - Logging and monitoring

3. **Template Method**
   - Base parser with customizable steps
   - Workflow execution framework
   - Plugin lifecycle management

## 🔄 Data Flow

### API Call Execution Flow

```
User Input
    ↓
Command Parser (CLI)
    ↓
Parameter Resolution
    ├→ Check Cache
    ├→ Check Context
    └→ Fetch from API
    ↓
Dependency Analysis
    ├→ Build Graph
    └→ Create Plan
    ↓
Execution Planning
    ├→ Optimize
    └→ Parallelize
    ↓
API Execution
    ├→ Authentication
    ├→ Rate Limiting
    └→ Error Handling
    ↓
Response Processing
    ├→ Extract Values
    ├→ Update Context
    └→ Cache Results
    ↓
Output Formatting
    ↓
User Display
```

## 💾 Data Models

### Core Models

```python
@dataclass
class APISpecification:
    """Unified internal API model"""
    endpoints: List[Endpoint]
    schemas: Dict[str, Schema]
    authentication: AuthConfig
    metadata: APIMetadata

@dataclass
class Endpoint:
    """Single API endpoint definition"""
    path: str
    method: HTTPMethod
    parameters: List[Parameter]
    request_body: Optional[Schema]
    responses: Dict[int, Response]
    dependencies: List[str]

@dataclass
class ExecutionPlan:
    """Plan for executing API calls"""
    steps: List[ExecutionStep]
    parallel_groups: List[List[ExecutionStep]]
    estimated_time: timedelta
    required_inputs: Dict[str, Any]
```

## 🔐 Security Architecture

### Authentication Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────>│   CLI       │────>│   Auth      │
│             │     │             │     │   Service   │
└─────────────┘     └─────────────┘     └─────────────┘
                            │                    │
                            ↓                    ↓
                    ┌─────────────┐     ┌─────────────┐
                    │  Encrypted  │     │    API      │
                    │   Storage   │     │   Server    │
                    └─────────────┘     └─────────────┘
```

### Security Measures

1. **Credential Protection**
   - Never store plain text passwords
   - Use Fernet encryption for sensitive data
   - Secure key derivation and storage

2. **Token Management**
   - Automatic token refresh
   - Secure token storage
   - Token expiration handling

3. **API Security**
   - Request signing support
   - OAuth2 flow implementation
   - API key rotation

## 🔌 Plugin Architecture

### Plugin Interface

```python
class Plugin(ABC):
    @abstractmethod
    def initialize(self, context: PluginContext) -> None
    
    @abstractmethod
    def execute(self, event: PluginEvent) -> PluginResult
    
    @abstractmethod
    def cleanup(self) -> None
```

### Plugin Lifecycle

1. **Discovery**: Scan plugin directories
2. **Loading**: Import and validate plugins
3. **Initialization**: Setup plugin resources
4. **Execution**: Handle plugin events
5. **Cleanup**: Release resources

### Plugin Types

- **Parsers**: Custom API format parsers
- **Adapters**: Output format adapters
- **Middleware**: Request/response processors
- **Extensions**: New CLI commands
- **Integrations**: Third-party service connectors

## 🚀 Performance Considerations

### Optimization Strategies

1. **Caching**
   - API response caching
   - Parsed specification caching
   - Execution plan caching

2. **Lazy Loading**
   - Load modules on demand
   - Defer expensive operations
   - Stream large responses

3. **Parallel Execution**
   - Concurrent API calls
   - Async I/O operations
   - Thread pool for CPU tasks

### Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Startup Time | <100ms | ~200ms |
| Dependency Resolution | <100ms | ~500ms |
| API Call Overhead | <10ms | Unknown |
| Memory Usage | <100MB | Unknown |

## 🔄 Scalability Design

### Horizontal Scaling

- Stateless design for easy scaling
- Distributed caching support
- Queue-based job processing

### Vertical Scaling

- Efficient memory usage
- Optimized algorithms
- Resource pooling

## 🧪 Testing Strategy

### Test Layers

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Component interaction testing
3. **End-to-End Tests**: Full workflow testing
4. **Performance Tests**: Load and stress testing
5. **Security Tests**: Vulnerability scanning

### Test Coverage Goals

- Unit Tests: 80% coverage
- Integration Tests: 60% coverage
- E2E Tests: Critical paths only
- Performance Tests: All bottlenecks

## 📚 Technology Stack

### Current Stack

- **Language**: Python 3.12
- **CLI Framework**: Typer
- **HTTP Client**: httpx/requests
- **Validation**: Pydantic
- **Encryption**: cryptography
- **Testing**: pytest
- **Linting**: ruff
- **Type Checking**: mypy

### Future Additions

- **Async**: asyncio/aiohttp
- **Caching**: Redis
- **Queue**: Celery/RQ
- **Monitoring**: OpenTelemetry
- **Database**: SQLite/PostgreSQL

---

*This architecture document represents the current and planned design. It will evolve as the project develops.*