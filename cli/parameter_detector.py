from enum import Enum, auto
from typing import Optional, Any, Dict, List, Pattern
import re
from dataclasses import dataclass


class ParameterType(Enum):
    """Types of parameters we can detect"""
    FOREIGN_KEY = auto()
    ENUM = auto()
    DATE = auto()
    DATETIME = auto()
    PAGINATION = auto()
    FILTER = auto()
    SORT = auto()
    SEARCH = auto()
    BOOLEAN = auto()
    NUMERIC = auto()
    STRING = auto()
    UNKNOWN = auto()


@dataclass
class ParameterInfo:
    """Information about a detected parameter"""
    name: str
    type: ParameterType
    likely_provider: Optional[str] = None
    is_required: bool = False
    schema_type: Optional[str] = None
    enum_values: Optional[List[str]] = None
    pattern: Optional[str] = None


class ParameterDetector:
    """Intelligent parameter type detection for OpenAPI parameters"""
    def __init__(self):
        # ID patterns that indicate foreign keys
        self.id_patterns: List[Pattern] = [
            re.compile(r'.*[Ii]d$'),      # ends with Id or id
            re.compile(r'^id$', re.I),    # exactly 'id' (case insensitive)
            re.compile(r'.*_id$'),        # ends with _id
            re.compile(r'.*[Ii]ds$'),     # plural IDs
            re.compile(r'^uuid$', re.I),  # UUID references
        ]
        # Map parameter names to likely endpoint providers
        self.reference_patterns: Dict[str, str] = {
            'merchantId': 'merchants',
            'merchantIds': 'merchants',
            'locationId': 'locations',
            'locationIds': 'locations',
            'userId': 'users',
            'userIds': 'users',
            'groupId': 'groups',
            'groupIds': 'groups',
            'roleId': 'roles',
            'channelId': 'channels',
            'orderId': 'orders',
            'incidentId': 'incidents',
            'rewardId': 'rewards',
            'surveyId': 'surveys',
            'questionnaireId': 'questionnaires',
            'snapshotId': 'snapshots',
            'deliveryServiceId': 'delivery-services',
            'partnerId': 'partners',
        }
        # Pagination parameters
        self.pagination_params = {
            'page', 'pagesize', 'limit', 'offset', 'skip',
            'per_page', 'perpage', 'size', 'start', 'cursor'
        }
        # Date/time patterns
        self.date_patterns = [
            re.compile(r'.*[Dd]ate$'),
            re.compile(r'.*[Dd]ate[Tt]ime$'),
            re.compile(r'.*[Tt]ime$'),
            re.compile(r'.*[Aa]t$'),  # createdAt, updatedAt, etc.
            re.compile(r'.*[Uu]tc$'),  # dateTimeUtc patterns
            re.compile(r'^(created|updated|modified|deleted)$', re.I),
        ]
        # Filter/search patterns
        self.filter_patterns = [
            re.compile(r'^filter.*', re.I),
            re.compile(r'^search.*', re.I),
            re.compile(r'^query.*', re.I),
            re.compile(r'.*[Ff]ilter$'),
            re.compile(r'.*[Ss]earch$'),
            re.compile(r'.*[Qq]uery$'),
        ]

    def detect_parameter_type(self, param_name: str, param_schema: dict) -> ParameterInfo:
        """
        Detect the type of a parameter based on its name and schema
        Args:
            param_name: The parameter name
            param_schema: The OpenAPI schema definition for the parameter
        Returns:
            ParameterInfo with detected type and metadata
        """
        info = ParameterInfo(
            name=param_name,
            type=ParameterType.UNKNOWN,
            is_required=param_schema.get('required', False),
            schema_type=param_schema.get('type'),
        )
        # Check for enum
        if 'enum' in param_schema:
            info.type = ParameterType.ENUM
            info.enum_values = param_schema['enum']
            return info
        # Check for foreign key patterns
        if self.is_foreign_key(param_name):
            info.type = ParameterType.FOREIGN_KEY
            info.likely_provider = self.get_likely_provider(param_name)
            return info
        # Check for pagination
        if param_name.lower() in self.pagination_params:
            info.type = ParameterType.PAGINATION
            return info
        # Check for dates
        if self._matches_patterns(param_name, self.date_patterns):
            schema_type = param_schema.get('type', '')
            schema_format = param_schema.get('format', '')
            if (
                schema_format == 'date-time' or
                'datetime' in param_name.lower()
            ):
                info.type = ParameterType.DATETIME
            else:
                info.type = ParameterType.DATE
            return info
        # Check for filters/search
        if self._matches_patterns(param_name, self.filter_patterns):
            if 'search' in param_name.lower():
                info.type = ParameterType.SEARCH
            else:
                info.type = ParameterType.FILTER
            return info
        # Check schema type
        schema_type = param_schema.get('type', '').lower()
        if schema_type == 'boolean':
            info.type = ParameterType.BOOLEAN
        elif schema_type in ['integer', 'number']:
            info.type = ParameterType.NUMERIC
        elif schema_type == 'string':
            info.type = ParameterType.STRING
        # Pattern detection
        if 'pattern' in param_schema:
            info.pattern = param_schema['pattern']
        return info

    def is_foreign_key(self, param_name: str) -> bool:
        """Check if a parameter name indicates a foreign key reference"""
        return self._matches_patterns(param_name, self.id_patterns)

    def get_likely_provider(self, param_name: str) -> Optional[str]:
        """
        Get the likely endpoint that provides this parameter
        Args:
            param_name: The parameter name to check
        Returns:
            The endpoint path that likely provides this parameter
        """
        # Direct lookup
        if param_name in self.reference_patterns:
            return self.reference_patterns[param_name]
        # Try case-insensitive lookup
        param_lower = param_name.lower()
        for key, value in self.reference_patterns.items():
            if key.lower() == param_lower:
                return value
        # Try to extract resource name from parameter
        # e.g., "customerId" -> "customers", "productId" -> "products"
        if self.is_foreign_key(param_name):
            # Remove ID suffix and pluralize
            base = re.sub(r'[Ii]ds?$|_id$', '', param_name)
            # Simple pluralization (can be enhanced)
            if base:
                return f"{base.lower()}s"
        return None

    def extract_id_from_response(
        self, 
        response_data: dict, 
        param_name: str
    ) -> Optional[Any]:
        """
        Extract an ID value from an API response
        Args:
            response_data: The API response data
            param_name: The parameter name we're looking for
        Returns:
            The extracted ID value, or None if not found
        """
        # Direct match
        if param_name in response_data:
            return response_data[param_name]
        # Check if response has 'data' wrapper
        if 'data' in response_data:
            if isinstance(response_data['data'], list):
                # For lists, we might need user selection
                # Return first item's ID for now
                if (
                    response_data['data'] and
                    param_name in response_data['data'][0]
                ):
                    return response_data['data'][0][param_name]
            elif isinstance(response_data['data'], dict):
                if param_name in response_data['data']:
                    return response_data['data'][param_name]
        # Try common variations
        variations = [
            param_name,
            param_name.lower(),
            param_name.upper(),
            self._camel_to_snake(param_name),
            self._snake_to_camel(param_name),
        ]
        for variant in variations:
            value = self._find_nested_value(response_data, variant)
            if value is not None:
                return value
        # Try to find any ID field if parameter ends with 'Id'
        if self.is_foreign_key(param_name):
            return self._find_any_id_field(response_data)
        return None

    def get_parameter_metadata(self, param_schema: dict) -> Dict[str, Any]:
        """Extract additional metadata from parameter schema"""
        metadata = {}
        # Extract constraints
        for constraint in [
            'minimum', 'maximum', 'minLength', 'maxLength',
            'minItems', 'maxItems', 'multipleOf'
        ]:
            if constraint in param_schema:
                metadata[constraint] = param_schema[constraint]
        # Extract format
        if 'format' in param_schema:
            metadata['format'] = param_schema['format']
        # Extract default
        if 'default' in param_schema:
            metadata['default'] = param_schema['default']
        # Extract description
        if 'description' in param_schema:
            metadata['description'] = param_schema['description']
        return metadata

    def _matches_patterns(self, text: str, patterns: List[Pattern]) -> bool:
        """Check if text matches any of the provided patterns"""
        return any(pattern.match(text) for pattern in patterns)

    def _find_nested_value(self, data: dict, key: str, max_depth: int = 3) -> Optional[Any]:
        """Recursively search for a key in nested dictionaries"""
        if max_depth <= 0:
            return None
        if key in data:
            return data[key]
        for value in data.values():
            if isinstance(value, dict):
                result = self._find_nested_value(value, key, max_depth - 1)
                if result is not None:
                    return result
        return None

    def _find_any_id_field(self, data: dict) -> Optional[Any]:
        """Find any field that looks like an ID"""
        for key, value in data.items():
            if (
                key.lower() == 'id' or
                key.lower().endswith('id')
            ):
                return value
        # Check in nested 'data' if present
        if 'data' in data:
            if isinstance(data['data'], dict):
                return self._find_any_id_field(data['data'])
            elif isinstance(data['data'], list) and data['data']:
                return self._find_any_id_field(data['data'][0])
        return None

    def _camel_to_snake(self, text: str) -> str:
        """Convert camelCase to snake_case"""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()

    def _snake_to_camel(self, text: str) -> str:
        """Convert snake_case to camelCase"""
        components = text.split('_')
        return components[0] + ''.join(x.title() for x in components[1:]) 