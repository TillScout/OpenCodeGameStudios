The free Lite edition — the complete inspect → author → run → see loop, for GDScript and C#:

Reflection / discovery: get_godot_version, find_classes, describe_class, find_methods, describe_object, set_property, call_method, get_scene_tree
Scene authoring (undoable): create_node, delete_node, rename_node, reparent_node, duplicate_node, move_node, instance_scene, save_scene, open_scene
GDScript dev-loop: validate_script, write_script, script_patch, read_script, attach_script
C#/.NET dev-loop: build_csharp (a dotnet build compile-check returning structured file:line:col + CS-code diagnostics, safe while the editor is open, zero new dependency; write_script is .cs-aware and C# [GlobalClass] types show up in reflection)
Signals: connect_signal, disconnect_signal, list_signals
Resource assets: create_resource, set_resource
Files / project: read_file, write_file, list_dir, search_files, get_project_setting, set_project_setting
Run loop: play_scene, stop_scene, get_play_state, wait_until, logs_read
Runtime observation (the AI sees your game): screenshot, ui_snapshot (every visible Control as structured state in one call), get_remote_tree, find_nodes, wait_for_node, runtime_get_property, monitor_properties, get_performance_monitors, game_logs
Render diagnosis: render_probe (why a 3D node is or is not on screen, as data: visibility chain, frustum, cull mask, material cull mode, triangle winding) and set_debug_draw (switch the running game's debug draw mode, then screenshot one render stage)
Project / authoring helpers: get_project_statistics, apply_template, batch_execute, doctor (one-call self-diagnosis: edition, effort cap, server and auth state, client configs, and what the tool list costs your context per tier), help (any tool's full argument catalogue, on demand)
MCP Resources: scene://tree, scene://selection, project://settings, assets://list, log://output, audit://recent
MCP Prompts: inspect_node, audit_scene, setup_2d_player, fix_script_errors, build_test_fix, make_game
