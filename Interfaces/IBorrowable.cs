namespace SimpleLibraryOop.Interfaces;

/// <summary>
/// 可被借閱的物件應具備的共同規格。
/// </summary>
public interface IBorrowable
{
    bool IsBorrowed { get; }

    string? BorrowerName { get; }

    bool Borrow(string borrowerName);

    bool Return();
}
