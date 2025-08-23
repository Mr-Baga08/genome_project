# mongo-init-scripts/init.js
// MongoDB initialization script
db = db.getSiblingDB('ugene_workflows');

// Create collections
db.createCollection('tasks');
db.createCollection('users');
db.createCollection('workflows');

// Create indexes
db.tasks.createIndex({ "task_id": 1 }, { unique: true });
db.tasks.createIndex({ "status": 1 });
db.tasks.createIndex({ "timestamps.created": -1 });
db.tasks.createIndex({ "priority": 1 });

// Create a default user (optional)
db.users.insertOne({
  _id: ObjectId(),
  username: "admin",
  email: "admin@ugene.local",
  created_at: new Date(),
  role: "admin"
});

print("Database initialized successfully");

