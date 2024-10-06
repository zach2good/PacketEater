CREATE VIEW submitter_summary AS
SELECT 
    s.id AS submitter_id,
    COUNT(DISTINCT cs.id) AS session_count,
    COUNT(pd.id) AS packet_count
FROM 
    submitters s
JOIN 
    sessions cs ON s.id = cs.submitter_id
LEFT JOIN 
    packet_data pd ON cs.id = pd.session_id
GROUP BY 
    s.id;
