export interface Entity {
  is_movable: boolean;  // Can be pushed/pulled
  is_jumpable: boolean;  // Can be jumped over
  is_usable_alone: boolean;  // Whether object can be used by itself
  is_collectable: boolean;  // Whether object can be collected
  is_wearable: boolean;  // Whether object can be worn
  weight: number;  // Weight affects movement mechanics
  usable_with: string[];  // IDs of objects this can be used with
  possible_alone_actions: string[];  // List of possible actions when used alone
  
} 