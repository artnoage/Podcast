import textgrad as tg
import os
try:
    from src.utils.utils import load_prompt, load_podcast_state, format_text_with_line_breaks
    from src.utils.agents_and_workflows import WeightClippingAgent
except ImportError:
    from utils.utils import load_prompt, load_podcast_state, format_text_with_line_breaks
    from utils.agents_and_workflows import WeightClippingAgent

def optimize_prompt(role, old_timestamp, new_timestamp, engine_model, backward_engine):
    # Set the backward engine
    tg.set_backward_engine(backward_engine, override=True)
    print(f"TextGrad backward engine set for {role}: {backward_engine}")

    # Determine the json_key based on the role
    if role == "summarizer":
        json_key = "main_text"
    elif role == "scriptwriter":
        json_key = "key_points"
    elif role == "enhancer":
        json_key = "script_essence"
    else:
        raise ValueError(f"Invalid role: {role}")

    # Load the prompt
    prompt = load_prompt(role, old_timestamp)

    # Define the system prompt
    system_prompt = tg.Variable(prompt, 
                                requires_grad=True, 
                                role_description=f"system prompt for {role}")

    # Define the LLM with the system prompt
    llm_engine = tg.get_engine(engine_model, override=True)
    model = tg.BlackboxLLM(llm_engine, system_prompt=system_prompt)

    # Load the podcast state using the new timestamp
    data = load_podcast_state(new_timestamp)

    # Define the user prompt (fixed) using the data from the JSON
    user_prompt = tg.Variable(data[json_key], 
                              requires_grad=False, 
                              role_description=f"input for {role}")

    # Define the target using the feedback from the JSON
    feedback = data["feedback"]
    target = tg.Variable(f"""create a detailed set of instructions for a ({role}) within a group consisting of a key_point extractor/summarizer from academic texts, 
                        a scriptwriter and a script enhancer, under the following three rules:
                        1) Role boundaries are clear. 
                        2) Guidelines are topic-agnostic/abstract enough. Any feedback maybe topic related but guidelines must be abstract enough to apply to any topic.
                        3) Guidelines are good enough to avoid the following feedback within the role of {role}. Feedback: """ + feedback, 
              requires_grad=False, 
              role_description=f"target output for {role}")

    # Define the loss function
    loss_fn = tg.TextLoss(target)

    # Set up the optimizer
    optimizer = tg.TGD(parameters=list(model.parameters()))

    # Optimization loop
    num_iterations = 5  # You can adjust this number
    for _ in range(num_iterations):
        # Forward pass
        output = model(user_prompt)
        
        # Compute loss
        loss = loss_fn(output)
        
        # Backward pass
        loss.backward()
        
        # Update the system prompt
        optimizer.step()
        optimizer.zero_grad()

    # Apply weight clipping
    weight_clipper = WeightClippingAgent()
    cleaned_prompt = weight_clipper.clean_prompt(system_prompt.value, role)

    print(f"\nCleaned System Prompt for {role}!")

    # Save the optimized and cleaned prompt to prompt_history folder with new timestamp
    os.makedirs("prompt_history", exist_ok=True)
    new_history_file = os.path.join("prompt_history", f"{role}_prompt.txt_{new_timestamp}")
    formatted_prompt = format_text_with_line_breaks(cleaned_prompt)
    with open(new_history_file, "w") as f:
        f.write(formatted_prompt)
    print(f"\nOptimized, cleaned, and formatted system prompt for {role} saved to '{new_history_file}'")

    return cleaned_prompt
