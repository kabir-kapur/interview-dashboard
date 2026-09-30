-- Replace the CSV bank and separate progress overlay with persisted problems.
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    link TEXT,
    topics TEXT,
    difficulty TEXT,
    companies TEXT,
    status TEXT NOT NULL DEFAULT 'not_started',
    status_updated_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

INSERT INTO problems(id, title, prompt, link, topics, difficulty, companies, status, status_updated_at, created_at) VALUES
    ('two-sum', 'Two Sum', 'Given an array of integers and a target, return indices of two values whose sum equals the target.', 'https://leetcode.com/problems/two-sum/', '["arrays", "hash map"]', 'Easy', '["Meta", "Amazon"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('valid-parentheses', 'Valid Parentheses', 'Determine whether a string containing brackets is valid and properly nested.', 'https://leetcode.com/problems/valid-parentheses/', '["stack", "strings"]', 'Easy', '["Google"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('longest-substring', 'Longest Substring Without Repeating Characters', 'Find the length of the longest substring with no repeated characters.', 'https://leetcode.com/problems/longest-substring-without-repeating-characters/', '["sliding window", "hash map"]', 'Medium', '["Amazon", "Microsoft"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('merge-intervals', 'Merge Intervals', 'Merge all overlapping intervals in a list of intervals.', 'https://leetcode.com/problems/merge-intervals/', '["intervals", "sorting"]', 'Medium', '["Meta"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('number-of-islands', 'Number of Islands', 'Count islands in a grid of land and water cells.', 'https://leetcode.com/problems/number-of-islands/', '["graphs", "dfs"]', 'Medium', '["Amazon", "Google"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('binary-tree-level-order', 'Binary Tree Level Order Traversal', 'Return the nodes of a binary tree level by level.', 'https://leetcode.com/problems/binary-tree-level-order-traversal/', '["trees", "bfs"]', 'Medium', '["Microsoft"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('coin-change', 'Coin Change', 'Find the fewest coins needed to make a given amount, or return -1 if it is impossible.', 'https://leetcode.com/problems/coin-change/', '["dynamic programming"]', 'Medium', '["Uber"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('kth-largest', 'Kth Largest Element in an Array', 'Return the kth largest element in an unsorted array.', 'https://leetcode.com/problems/kth-largest-element-in-an-array/', '["heap", "arrays"]', 'Medium', '["Meta", "Amazon"]', 'not_started', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT(id) DO NOTHING;

ALTER TABLE plans RENAME TO daily_plans;

DROP TABLE IF EXISTS progress;
DROP TABLE IF EXISTS digest_deliveries;
