"""Bind research scalers to the roles populated by one fresh model."""


def keep_active_groups(optimizers):
    """Omit empty templates before a scaler captures fresh ownership."""
    omitted = []
    for optimizer in optimizers:
        active = [group for group in optimizer.param_groups if group["params"]]
        if not active or optimizer.state:
            raise ValueError("fresh optimizer with populated ownership required")
        omitted.append(len(optimizer.param_groups) - len(active))
        optimizer.param_groups[:] = active
    return omitted
